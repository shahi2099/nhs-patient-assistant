import json
import re

def chunk_by_markdown(record):
    """
    Split a markdown document into chunks using ## headings.

    Parameters
    ----------
    record : dict

    Returns
    -------
    list[dict]
    """

    text = record["content"]

    # split by H2 and H3
    parts = re.split(r"(?=^#{2,3}\s)", text, flags=re.MULTILINE)    

    parts = [p for p in parts if p.strip()]

    chunks = []

    for i, part in enumerate(parts):

        part = part.strip()

        if not part:
            continue

        heading = ""

        first_line = part.splitlines()[0]

        heading = re.sub(r"^#{2,3}\s*", "", first_line).strip() # Remove the Markdown heading symbols from the beginning of the line.  

        chunks.append({
            "chunk_id": f"{record['id']}-{i+1}",
            "parent_id": record["id"],
            "category": record["category"],
            "section": record["section"],
            "heading": heading,
            "url": record["url"],
            "content": part,
        })

    return chunks



# Load records
with open("data/nhs-symptom.json", "r", encoding="utf-8") as f:
    records = json.load(f)

# Chunk all records
all_chunks = []

for record in records:
    chunks = chunk_by_markdown(record)
    all_chunks.extend(chunks)

# Save chunks
with open("data/nhs-symptom-chunks.json", "w", encoding="utf-8") as f:
    json.dump(all_chunks, f, ensure_ascii=False, indent=2)

print(f"Processed {len(records)} records")
print(f"Created {len(all_chunks)} chunks")
print("Saved to data/nhs-symptom-chunks.json")

