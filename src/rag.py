import json
from time import time
from openai import OpenAI
from pydantic_ai import Agent
from db import keyword_search, pgvector_search
from sentence_transformers import SentenceTransformer

from dotenv import load_dotenv
load_dotenv()

openai_client = OpenAI()
model = SentenceTransformer('all-MiniLM-L6-v2')

#
#
def llm(prompt, model="gpt-5.4-mini"):
    response = openai_client.responses.create(
        model=model,
        input=[{"role": "user", "content": prompt}]
    )

    answer = response.output_text
    token_stats = {
        "prompt_tokens": response.usage.input_tokens,
        "completion_tokens": response.usage.output_tokens,
        "total_tokens": response.usage.total_tokens,
    }
    return answer, token_stats


def rewrite_query(question):

    prompt = f"""
You are a search query optimizer for an NHS medical document retrieval system.

Rewrite the user's question into a short keyword-based search query
for retrieving relevant NHS medical documents.

Rules:
- Remove conversational phrases such as "I've had", "should I", "do I need", "what should I do".
- Keep the main medical concepts from the user's question.
- Keep symptoms, conditions, body parts, treatments, medications, and risk factors.
- Convert everyday wording into common medical terms where appropriate.
- Keep clinically important qualifiers such as severity, urgency, duration, age group, or risk factors when they help retrieval.
- Remove generic words that do not improve retrieval, such as "medical help", "advice", "information", unless they are essential.
- Do not add diagnoses, symptoms, or treatments that are not mentioned by the user.
- Prefer 3-8 meaningful search terms.
- Optimise for high recall in NHS document retrieval.
- Return only the rewritten search query.

User question:
{question}

Rewritten query:
"""

    return llm(prompt)


def rrf(search_results, k=1, num_results=5): 
    scores = {}
    doc_map = {}

    for results in search_results:
        for rank, doc in enumerate(results):
            key = doc["chunk_id"]
            if key not in scores:
                scores[key] = 0
                doc_map[key] = doc
            scores[key] += 1 / (k + rank + 1)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [doc_map[key] for key, _ in ranked[:num_results]]


def hybrid_search(query, num_results=5):
    original_query = query
    rewritten_query, _ = rewrite_query(query)

    vector_results = pgvector_search(query=original_query,model=model,num_results=num_results)
    keyword_results = keyword_search(query=rewritten_query,num_results=num_results)

    return rrf([keyword_results, vector_results], num_results=num_results)    


# 
# evaluation
#

evaluation_prompt_template = """
You are an expert evaluator for a RAG system.
Your task is to analyze the relevance of the generated answer to the given question.
Based on the relevance of the generated answer, you will classify it
as 'NON_RELEVANT', 'PARTLY_RELEVANT', or 'RELEVANT'.

Here is the data for evaluation:

Question: {question}
Generated Answer: {answer}

Please analyze the content and context of the generated answer in relation to the question
and provide your evaluation in parsable JSON without using code blocks:

{{
  'Relevance': 'NON_RELEVANT' | 'PARTLY_RELEVANT' | 'RELEVANT',
  'Explanation': '[Provide a brief explanation for your evaluation]'
}}
""".strip()

# Define the evaluation and cost functions:
def evaluate_relevance(question, answer):
    prompt = evaluation_prompt_template.format(question=question, answer=answer)
    evaluation, tokens = llm(prompt, model="gpt-5.4-mini")

    try:
        json_eval = json.loads(evaluation)
        return json_eval, tokens
    except json.JSONDecodeError:
        result = {"Relevance": "UNKNOWN", "Explanation": "Failed to parse evaluation"}
        return result, tokens

def calculate_openai_cost(model, tokens):
    openai_cost = 0
    if "gpt-5.4-mini" in model:
        openai_cost = (
            tokens["prompt_tokens"] * 0.15
            + tokens["completion_tokens"] * 0.60
        ) / 1_000_000
    return openai_cost


# 
# agentic_rag implementation
#

def hybrid_search_text(query, num_results=5):
    """
    Search the NHS knowledge base.

    Args:
        query (str): The search query string.
        num_results(int): The number of results

    Returns:
        List[Dict]: A list of up to 5 search results returned by the index.
    """
    
    return hybrid_search(query=query, num_results=5)


system_prompt = """
You are an NHS assistant expert.

You MUST call hybrid_search_text before answering ANY question.

You may call the tool multiple times if needed, especially to refine or correct search queries.

When answering:
- Always use the hybrid_search_text tool before answering.
- You may rephrase or correct the query (e.g. spelling mistakes) to improve retrieval.
- If retrieved context is relevant, use it as the main source of truth.
- If context is partially relevant, use it to construct the best possible answer grounded in it.
- Only say you don't have enough information if no relevant medical information is found after multiple searches.
- Do not hallucinate or use outside knowledge.
""".strip()


from pydantic import BaseModel

class NHSAnswer(BaseModel):
    answer: str
    used_context: bool

def agentic_rag(query, model="gpt-5.4-mini"):
    t0 = time()

    agent = Agent(
        name="nhs_agent",
        instructions=system_prompt,
        tools=[hybrid_search_text],
        output_type=NHSAnswer,
        model="openai:gpt-5.4-mini"
    )

    result = agent.run_sync(query)
    answer = result.output.answer

    token_stats = {
        "prompt_tokens": result.usage.input_tokens,
        "completion_tokens": result.usage.output_tokens,
        "total_tokens": result.usage.total_tokens,
    }


    relevance, rel_token_stats = evaluate_relevance(query, answer)

    t1 = time()
    took = t1 - t0

    openai_cost_rag = calculate_openai_cost(model, token_stats)    
    openai_cost_eval = calculate_openai_cost(model, rel_token_stats)
    openai_cost = openai_cost_rag + openai_cost_eval

    return {
        "answer": answer,
        "model_used": model,
        "response_time": took,
        "relevance": relevance.get("Relevance", "UNKNOWN"),
        "relevance_explanation": relevance.get("Explanation", "Failed to parse"),
        "prompt_tokens": token_stats["prompt_tokens"],
        "completion_tokens": token_stats["completion_tokens"],
        "total_tokens": token_stats["total_tokens"],
        "eval_prompt_tokens": rel_token_stats["prompt_tokens"],
        "eval_completion_tokens": rel_token_stats["completion_tokens"],
        "eval_total_tokens": rel_token_stats["total_tokens"],
        "openai_cost": openai_cost,
    }


