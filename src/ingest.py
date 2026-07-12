import os
import json
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import db

from dotenv import load_dotenv
load_dotenv()

# The ingestion script loads the json and builds the search index. data is stored in the db.
DATA_PATH = os.getenv("DATA_PATH", "data/nhs-symptom-chunks.json")
model = SentenceTransformer('all-MiniLM-L6-v2')
openai_client = OpenAI()

#
# fetch the nhs dataset. 
def load_dataset(data_path=DATA_PATH):   

    with open(data_path, "r", encoding="utf-8") as f:
        documents = json.load(f)

    texts = []

    for doc in documents:
        text = doc['section'] + ' ' + doc['heading'] + doc['content']
        texts.append(text)


    batch_size = 50
    vectors = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_vectors = model.encode(batch)
        vectors.extend(batch_vectors)

    db.insert_documents(documents,vectors)

if __name__ == "__main__":
    load_dataset()
