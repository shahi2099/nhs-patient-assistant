import os
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime
from zoneinfo import ZoneInfo

TZ_INFO = os.getenv("TZ", "Europe/London")
tz = ZoneInfo(TZ_INFO)

# Normally export as env variables. use here for demo.
#
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),   
        database=os.getenv("POSTGRES_DB", "nhs-patient-assistant"),
        user=os.getenv("POSTGRES_USER", "user"),
        password=os.getenv("POSTGRES_PASSWORD", "password"),
    )

#
# Set-up to create tables. conversation, feedback and documents.
def init_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS feedback")
            cur.execute("DROP TABLE IF EXISTS conversations")
            cur.execute("DROP TABLE IF EXISTS documents")
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")            


            cur.execute("""
                CREATE TABLE conversations (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    model_used TEXT NOT NULL,
                    response_time FLOAT NOT NULL,
                    relevance TEXT NOT NULL,
                    relevance_explanation TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    eval_prompt_tokens INTEGER NOT NULL,
                    eval_completion_tokens INTEGER NOT NULL,
                    eval_total_tokens INTEGER NOT NULL,
                    openai_cost FLOAT NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE feedback (
                    id SERIAL PRIMARY KEY,
                    conversation_id TEXT REFERENCES conversations(id),
                    feedback INTEGER NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
                )
            """)

            cur.execute("""
                CREATE TABLE documents (
                    id SERIAL PRIMARY KEY,
                    chunk_id    TEXT,
                    parent_id   TEXT,            
                    section TEXT,
                    heading TEXT,
                    content TEXT,
                    embedding vector(384),
                    search_vector tsvector GENERATED ALWAYS AS (
                        to_tsvector(
                            'english',
                            coalesce(section, '') || ' ' ||
                            coalesce(heading, '') || ' ' ||
                            coalesce(content, '')
                        )
                    ) STORED
                )
            """)
            cur.execute("""
                 CREATE INDEX documents_embedding_idx
                 ON documents
                 USING hnsw (embedding vector_cosine_ops)
             """)
            cur.execute("""
                 CREATE INDEX documents_search_vector_idx
                 ON documents
                 USING gin (search_vector)
             """)

        conn.commit()
    finally:
        conn.close()

#
# user conversations saved.
def save_conversation(conversation_id, question, answer_data, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now(tz)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversations
                (id, question, answer, model_used, response_time, relevance,
                relevance_explanation, prompt_tokens, completion_tokens, total_tokens,
                eval_prompt_tokens, eval_completion_tokens, eval_total_tokens,
                openai_cost, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    conversation_id,
                    question,
                    answer_data["answer"],
                    answer_data["model_used"],
                    answer_data["response_time"],
                    answer_data["relevance"],
                    answer_data["relevance_explanation"],
                    answer_data["prompt_tokens"],
                    answer_data["completion_tokens"],
                    answer_data["total_tokens"],
                    answer_data["eval_prompt_tokens"],
                    answer_data["eval_completion_tokens"],
                    answer_data["eval_total_tokens"],
                    answer_data["openai_cost"],
                    timestamp
                ),
            )
        conn.commit()
    finally:
        conn.close()

#
# user feedback saved
def save_feedback(conversation_id, feedback, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now(tz)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO feedback (conversation_id, feedback, timestamp) VALUES (%s, %s, %s)",
                (conversation_id, feedback, timestamp),
            )
        conn.commit()
    finally:
        conn.close()
        

def vec_to_str(vector):
    return '[' + ','.join(str(x) for x in vector) + ']'

#
# load all documents so it's persistent in db.
def insert_documents(documents,vectors):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:

            # Remove all existing rows
            cur.execute("TRUNCATE TABLE documents RESTART IDENTITY")                   

            # Insert fresh data. 
            # note: search_vector column is implicitly updated for key-word search.
            for doc, vec in zip(documents, vectors):
                cur.execute(
                    """
                    INSERT INTO documents (chunk_id, parent_id, section, heading, content, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s::vector)
                    """,
                    (doc['chunk_id'], doc['parent_id'], doc['section'], doc['heading'], doc['content'],
                     vec_to_str(vec))
                )

        conn.commit()
    finally:
        conn.close()     


def keyword_search(query, num_results=10):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    chunk_id,
                    section,
                    heading,
                    content,
                    ts_rank(
                        search_vector,
                        websearch_to_tsquery(
                            'english',
                            replace(%s, ' ', ' OR ')
                        )
                    ) AS score
                FROM documents
                WHERE search_vector @@ websearch_to_tsquery(
                    'english',
                    replace(%s, ' ', ' OR ')
                )
                ORDER BY score DESC
                LIMIT %s
                """,
                (query, query, num_results)
            )

            rows = cur.fetchall()            

    finally:
        conn.close()   

    return [
        {   'chunk_id': r[0],
            'section': r[1],
            'heading': r[2],
            'content': r[3]
        }
        for r in rows
    ]


def pgvector_search(query, model, num_results=10):
    conn = get_db_connection()
    query_vector = model.encode(query)
    query_str = vec_to_str(query_vector)
    try:
        with conn.cursor() as cur:
             cur.execute(
                 """
                 SELECT chunk_id, section, heading, content
                 FROM documents
                 ORDER BY embedding <=> %s::vector
                 LIMIT %s
                 """,
                 (query_str, num_results)
             )

             rows = cur.fetchall()

    finally:
        conn.close()   

    return [
        {'chunk_id':r[0], 'section': r[1], 'heading': r[2], 'content': r[3]}
        for r in rows
    ]

