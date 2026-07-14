
# NHS Patient Assistant

An end-to-end Retrieval-Augmented Generation (RAG) application that provides grounded answers using NHS Inform Scotland content, the official public health information service for Scotland.

The application combines hybrid retrieval (keyword + vector search), query rewriting, Reciprocal Rank Fusion (RRF), and GPT-5.4-mini to generate grounded responses.

---

## Demo
Watch the demo interface in action:

![Dashboard](images/demo.gif)

---

## Table of Contents 

- Problem Description
- Architecture
- Dataset
- Automated Ingestion Pipeline
- Retrieval Flow
- Retrieval Evaluation
- LLM Evaluation
- Interface
- Monitoring
- Project Structure
- Installation
- Test the API Locally (Optional)
- Evaluation Mapping
- Technologies
- Future Improvements

---

# Problem Description

Patients frequently search the internet for medical advice. Large language models can produce convincing but incorrect medical information if they rely only on their internal knowledge.

This project builds an end-to-end Retrieval-Augmented Generation (RAG) assistant grounded on the **NHS Inform Scotland** knowledge base. Instead of answering purely from model knowledge, responses are generated from relevant NHS documentation retrieved from a PostgreSQL knowledge base.

The application allows users to:

- Ask questions about illnesses and conditions
- Receive answers grounded in NHS Inform Scotland content
- Provide feedback on responses
- Monitor usage through Grafana dashboards

---

# Architecture

```text
                NHS Inform Scotland
                        │
                 nhs_download.py
                        │
              nhs-symptom.json (~425)
                        │
             nhs_chunking_data.py
                        │
         nhs-symptom-chunks.json (~6855)
                        │
                  ingest.py
                        │
       PostgreSQL + pgvector + FTS
                        │
                Hybrid Retrieval
        (Keyword + Vector + RRF)
                        │
               GPT-5.4-mini
                        │
                Streamlit UI
                        │
          Flask REST API (/question, /feedback)
                        │
          PostgreSQL Conversation Logs
                        │
                  Grafana Dashboard
```

---

# Dataset

Source:

NHS Inform Scotland A–Z of Illnesses and Conditions, the official public health information website for Scotland.

https://www.nhsinform.scot/illnesses-and-conditions/a-to-z/

## Raw Dataset

- 425 NHS illness and condition pages
- Stored as [`data/nhs-symptom.json`](data/nhs-symptom.json)
- Data is downloaded as part of Automated Ingestion Pipeline. The code is [`src/nhs_download.py`](src/nhs_download.py)

Each record contains:

- ID
- category
- section
- URL
- Markdown content

## Chunked Dataset

- 6,855 chunks
- Stored as [`data/nhs-symptom-chunks.json`](data/nhs-symptom-chunks.json)
- Data is generated as part of Automated Ingestion Pipeline. The code is [`src/nhs_chunking_data.py`](src/nhs_chunking_data.py) 

Each chunk contains:

- chunk ID
- parent ID
- category
- section
- parent document
- heading
- Markdown content
- URL

Heading-aware chunking improves retrieval quality while preserving document structure.

---

# Automated Ingestion Pipeline

The entire ingestion process is automated.

```text
make update-data
      │
      ├── download
      │     └── nhs_download.py
      │           ↓
      │    nhs-symptom.json
      │
      ├── chunk
      │     └── nhs_chunking_data.py
      │           ↓
      │    nhs-symptom-chunks.json
      │
      └── ingest
            └── ingest.py
                  ↓
        PostgreSQL Knowledge Base
```

Run:

```bash
make update-data
```

---

# Retrieval Flow

```text
User Question
      │
Hybrid Retrieval
 ├── Keyword Search/ Query Rewrite
 └── Vector Search
      │
Reciprocal Rank Fusion
      │
Top Documents
      │
GPT-5.4-mini
      │
Grounded Answer
```

The application combines:

- PostgreSQL Full Text Search
- pgvector semantic search
- Reciprocal Rank Fusion (RRF)
- Query rewriting

Both a knowledge base and an LLM are used in the flow.

---

# Retrieval Evaluation

To identify the most effective retrieval strategy, multiple retrieval approaches were evaluated using a ground truth dataset generated from 100 NHS documents (2 questions per document). The dataset is in [`data/ground-truth-retrieval.csv`](data/ground-truth-retrieval.csv)

| Method | Hit Rate | MRR |
|---------|---------:|----:|
| Keyword |0.800|0.596|
| Keyword + Query Rewrite|0.865|0.633|
| Vector|0.850|0.640|
| **Hybrid (Selected)**|**0.950**|**0.690**|

The hybrid retrieval approach achieved the highest Hit Rate and MRR and was therefore selected as the retrieval method used by the application.

Retrieval evaluation notebook:

- [`notebooks/nhs_search_pgdb.ipynb`](notebooks/nhs_search_pgdb.ipynb): Retrieval evaluation.
- [`notebooks/nhs_ground_truth_generation.ipynb`](notebooks/nhs_ground_truth_generation.ipynb): Ground truth dataset generation.

---

# LLM Evaluation

To identify the best LLM for answer generation, multiple models were evaluated using an LLM-as-a-Judge approach.

| Model | Relevant | Partly Relevant |
|-------|----------:|----------------:|
| GPT-5.4-mini |98.0%|2.0%|
| GPT-4o|91.5%|8.5%|

GPT-5.4-mini achieved the highest relevance score and was therefore selected as the model used by the application.

LLM evaluation notebook:

- [`notebooks/nhs_llm_eval.ipynb`](notebooks/nhs_llm_eval.ipynb): evaluation models


Evaluation data:

- [`data/rag-eval-gpt-4o.csv`](data/rag-eval-gpt-4o.csv)
- [`data/rag-eval-gpt-5.4-mini.csv`](data/rag-eval-gpt-5.4-mini.csv)

---

# Interface

## Streamlit

```
uv run streamlit run src/streamlit_app.py
```

Open:

```
http://localhost:8501
```

Screenshot:

![Dashboard](images/chat_assistant.PNG)


The interface supports:

- Asking questions
- Viewing responses
- Feedback collection

---

# Monitoring

Grafana dashboards monitor application behaviour.

Features include:

- User feedback
- Token usage
- Response latency
- Retrieval metrics
- Conversation
- Model usage
- Cost

Open:

```
http://localhost:3000
```

Dashboard configuration:


[`data/grafana.json`](data/grafana.json)

Screenshot:

![Dashboard](images/dash.PNG)

---

# Project Structure

```text
src/
    app.py
    rag.py
    db.py
    db_prep.py
    ingest.py
    nhs_download.py
    nhs_chunking_data.py
    streamlit_app.py

data/
    nhs-symptom.json
    nhs-symptom-chunks.json
    ground-truth-retrieval.csv
    rag-eval-gpt-5.4-mini.csv
    rag-eval-gpt-4o.csv
    grafana.json

notebooks/
    nhs_chunking.ipynb
    nhs_ground_truth_generation.ipynb
    nhs_search_pgdb.ipynb
    nhs_llm_eval.ipynb
```

---

# Installation

## 1. Clone the repository

```bash
git clone https://github.com/shahi2099/nhs-patient-assistant.git
cd nhs-patient-assistant
```

## 2. Install dependencies

```bash
uv sync
```

## 3. update .env.example

```text
copy .env.example to .env, then update the key.

OPENAI_API_KEY='YOUR_KEY'
```

## 4. Start containers

```bash
# Start all services (Postgres, app, and Grafana) - everything is in docker-compose.
docker compose up -d
```

## 5. Prepare database schema

```bash
# Create the PostgreSQL schema, tables, and indexes.
export POSTGRES_HOST=localhost
uv run python src/db_prep.py
```

## 6. Download and ingest data

```bash
# Download the latest NHS Inform Scotland data and ingest it into PostgreSQL.
export POSTGRES_HOST=localhost
make update-data
```

## 7. Start Streamlit

```bash
uv run streamlit run src/streamlit_app.py
```

---

# Test the API Locally (Optional)

```bash
curl -X POST http://localhost:5000/question \
-H "Content-Type: application/json" \
-d '{"question":"I hurt my lower back lifting something heavy. What should I do?"}'
```

Feedback:

```bash
curl -X POST http://localhost:5000/feedback \
-H "Content-Type: application/json" \
-d '{"conversation_id":"<id>","feedback":1}'
```

---

# Evaluation Mapping

| Requirement | Status |
|------------|--------|
| Problem Description | ✅ |
| Retrieval Flow | ✅ |
| Retrieval Evaluation | ✅ |
| LLM Evaluation | ✅ |
| Streamlit UI | ✅ |
| Flask API | ✅ |
| Automated Ingestion Pipeline | ✅ |
| Monitoring Dashboard | ✅ |
| User Feedback | ✅ |
| Docker Compose | ✅ |
| Reproducibility | ✅ |
| Hybrid Search | ✅ |
| Document re-ranking | ✅ |
| User query rewriting | ✅ |

---

# Technologies

- Python
- PostgreSQL
- pgvector
- OpenAI GPT-5.4-mini
- Flask
- Streamlit
- Grafana
- Docker Compose
- UV

---

# Future Improvements

- Cloud deployment
- Conversation memory
- Incremental updates
- Authentication
- Additional NHS datasets

---

# License

This project was developed for learning purposes using publicly available NHS Inform Scotland content.
