import os
import sys

# Add parent directory to path so we can import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from backend.app.config import CHROMA_DB_DIR

def view_embeddings():
    print("Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    
    try:
        collection = client.get_collection(name="mutual_fund_faq")
    except Exception as e:
        print(f"Error: Collection not found! Has it been populated? Details: {e}")
        return
        
    count = collection.count()
    print(f"Total documents/chunks in database: {count}")
    
    if count == 0:
        print("Database is empty. Run startup or evaluation script to populate data.")
        return
        
    print("\nRetrieving sample chunks and their embeddings (limit 5)...")
    # Fetch first 5 items from the database
    data = collection.get(limit=5, include=["documents", "metadatas", "embeddings"])
    
    ids = data.get("ids", [])
    documents = data.get("documents", [])
    metadatas = data.get("metadatas", [])
    embeddings = data.get("embeddings", [])
    
    for idx, (cid, doc, meta, emb) in enumerate(zip(ids, documents, metadatas, embeddings), 1):
        print("=" * 60)
        print(f"Sample Chunk #{idx}")
        print("=" * 60)
        print(f"Chunk ID: {cid}")
        print(f"Scheme Name: {meta.get('scheme_name')}")
        print(f"Section Name: {meta.get('section_name')}")
        safe_doc = doc[:150].replace('\u20b9', 'Rs ').encode('ascii', 'ignore').decode('ascii').replace(chr(10), ' ')
        print(f"Text Snippet: {safe_doc}...")
        if emb is not None:
            print(f"Embedding Dimensions: {len(emb)}")
            print(f"Embedding Vector (First 10 values): {emb[:10]} ...")
        else:
            print("Embedding Vector: None")
        print()

if __name__ == "__main__":
    view_embeddings()
