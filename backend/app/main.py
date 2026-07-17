import os
import uuid
import re
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.config import HOST, PORT, RAW_DATA_DIR
from backend.app.database import get_collection_count, insert_chunks, initialize_bm25, collection
from backend.app.orchestrator import process_query
from backend.scripts.ingest import fetch_and_save

app = FastAPI(title="Mutual Fund FAQ RAG Assistant", version="1.0.0")

# Enable CORS for frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow any local development environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

def chunk_by_sections(content: str, file_name: str, date_str_val: str) -> list[dict]:
    # Extract headers and body content
    lines = content.split("\n")
    metadata = {}
    body_start_idx = 0
    for idx, line in enumerate(lines[:8]):
        if line.startswith("Content:"):
            body_start_idx = idx + 1
            break
        if ":" in line:
            k, v = line.split(":", 1)
            key = k.strip().lower().replace(" ", "_")
            metadata[key] = v.strip()
            body_start_idx = idx + 1
            
    body_lines = lines[body_start_idx:]
    
    # 1. Filter out manager's other schemes list dynamically if it wasn't caught
    filtered_lines = []
    skip_mode = False
    for line in body_lines:
        l_strip = line.strip()
        if not l_strip:
            continue
        if "also manages these schemes" in l_strip.lower():
            skip_mode = True
            continue
        if skip_mode:
            # Stop skipping when we hit another header
            if any(h in l_strip.lower() for h in ["about", "exit load", "fund management", "minimum investments", "holdings", "key statistics", "process to"]):
                skip_mode = False
            else:
                continue
        filtered_lines.append(l_strip)
        
    body_text = "\n".join(filtered_lines)
    source_url = metadata.get("url", metadata.get("source_url", ""))
    scheme_name = metadata.get("scheme_name", metadata.get("title", file_name.replace(".txt", "").replace("_", " ").title()))
    
    # 2. Split body text on logical section headers
    patterns = [
        r"(Exit load, stamp duty and tax)",
        r"(Fund management)",
        r"(About\s+HDFC\s+[\w\s\-]+)",
        r"(Minimum investments)",
        r"(Returns and rankings)",
        r"(Holdings)",
        r"(Key Statistics\s*&\s*Metrics)",
        r"(Process to download statements)"
    ]
    pattern = "|".join(patterns)
    parts = re.split(pattern, body_text, flags=re.IGNORECASE)
    parts = [p for p in parts if p is not None]
    
    sections = []
    current_section = "General"
    
    idx = 0
    while idx < len(parts):
        part = parts[idx].strip()
        if not part:
            idx += 1
            continue
            
        # Check if it is a header
        is_header = False
        for ph in ["exit load, stamp duty and tax", "fund management", "about hdfc", "minimum investments", "returns and rankings", "holdings", "key statistics", "process to download"]:
            if ph in part.lower():
                is_header = True
                break
                
        if is_header:
            current_section = part
            if idx + 1 < len(parts):
                content_part = parts[idx+1].strip()
                if content_part:
                    sections.append((current_section, content_part))
                idx += 2
            else:
                idx += 1
        else:
            sections.append((current_section, part))
            idx += 1
            
    # 3. Create chunks from sections, preserving sentence boundaries
    chunks = []
    chunk_index = 0
    
    for sec_name, sec_text in sections:
        # Split section into sentences
        sentences = re.split(r'(?<=[.!?])\s+', sec_text)
        
        current_chunk_sentences = []
        current_chunk_len = 0
        
        for sent in sentences:
            sent_strip = sent.strip()
            if not sent_strip:
                continue
                
            sent_len = len(sent_strip)
            # If adding this sentence exceeds 500 characters, save the current chunk and start a new one
            if current_chunk_len + sent_len > 500:
                if current_chunk_sentences:
                    chunk_text_str = " ".join(current_chunk_sentences)
                    chunks.append({
                        "id": f"{file_name.replace('.txt', '')}_chunk_{chunk_index}",
                        "text": f"Scheme Context: {scheme_name} | Section: {sec_name}\n{chunk_text_str}",
                        "metadata": {
                            "scheme_name": scheme_name,
                            "source_url": source_url,
                            "last_updated": metadata.get("date_fetched", metadata.get("last_updated_date", date_str_val)),
                            "document_type": "groww_page",
                            "section_name": sec_name
                        }
                    })
                    chunk_index += 1
                
                # Start new chunk
                current_chunk_sentences = [sent_strip]
                current_chunk_len = sent_len
            else:
                current_chunk_sentences.append(sent_strip)
                current_chunk_len += sent_len + 1 # +1 for space
                
        if current_chunk_sentences:
            chunk_text_str = " ".join(current_chunk_sentences)
            chunks.append({
                "id": f"{file_name.replace('.txt', '')}_chunk_{chunk_index}",
                "text": f"Scheme Context: {scheme_name} | Section: {sec_name}\n{chunk_text_str}",
                "metadata": {
                    "scheme_name": scheme_name,
                    "source_url": source_url,
                    "last_updated": metadata.get("date_fetched", metadata.get("last_updated_date", date_str_val)),
                    "document_type": "groww_page",
                    "section_name": sec_name
                }
            })
            chunk_index += 1
            
    return chunks

@app.on_event("startup")
def startup_db_check():
    """
    On startup, verify that the Vector Database contains documents.
    If empty, run ingestion pipeline automatically.
    If database is not empty, check if raw files on disk have been updated
    since the last database ingestion, and re-index if needed.
    """
    print("Checking database population status...")
    count = get_collection_count()
    
    needs_reindex = False
    
    if count == 0:
        needs_reindex = True
    else:
        # Check if the last_updated date of files on disk is newer than what's in the DB
        try:
            # Get existing metadatas from Chroma
            existing_data = collection.get(include=["metadatas"])
            metadatas = existing_data.get("metadatas", [])
            
            db_updates = {}
            for meta in metadatas:
                url = meta.get("source_url", "").lower().strip()
                l_up = meta.get("last_updated", "")
                if url and l_up:
                    # Keep track of the latest date we have for each scheme/url
                    db_updates[url] = max(db_updates.get(url, ""), l_up)
            
            # Read files on disk and find their dates
            for file_name in os.listdir(RAW_DATA_DIR):
                if file_name.endswith(".txt"):
                    file_path = os.path.join(RAW_DATA_DIR, file_name)
                    
                    file_date = None
                    file_url = None
                    with open(file_path, "r", encoding="utf-8") as f:
                        for _ in range(10):
                            line = f.readline()
                            if not line:
                                break
                            if line.startswith("Date Fetched:"):
                                file_date = line.split(":", 1)[1].strip()
                            elif line.startswith("Last Updated Date:"):
                                file_date = line.split(":", 1)[1].strip()
                            elif line.startswith("URL:"):
                                file_url = line.split(":", 1)[1].strip().lower()
                            elif line.startswith("Source URL:"):
                                file_url = line.split(":", 1)[1].strip().lower()
                                
                    if not file_url:
                        # Fallback mapping from config based on filename keyword
                        from backend.app.config import GROWW_URLS
                        for u in GROWW_URLS:
                            name_part = file_name.replace(".txt", "").replace("_", "-")
                            if name_part in u:
                                file_url = u.lower().strip()
                                break
                        
                    # If we don't find a date in the file, use mtime date
                    if not file_date:
                        import datetime
                        mtime = os.path.getmtime(file_path)
                        file_date = datetime.date.fromtimestamp(mtime).isoformat()
                        
                    # Compare dates
                    db_date = db_updates.get(file_url)
                    if not db_date:
                        print(f"URL '{file_url}' not found in database. Triggering re-index...")
                        needs_reindex = True
                        break
                    elif file_date > db_date:
                        print(f"File '{file_name}' (date: {file_date}) is newer than DB record (date: {db_date}). Triggering re-index...")
                        needs_reindex = True
                        break
        except Exception as e:
            print(f"Error checking for raw updates: {e}. Defaulting to skip re-indexing.")
            
    if needs_reindex:
        if count == 0:
            print("Vector database is empty! Auto-triggering data ingestion pipeline...")
            fetch_and_save()
        else:
            print("Updates detected. Re-indexing database...")
        reindex_all_documents()
    else:
        print(f"Vector database up to date. {count} indexed text chunks active.")
        initialize_bm25()

def reindex_all_documents():
    """
    Purges existing document chunks in ChromaDB and re-chunks/re-embeds raw documents.
    """
    print("Purging vector database...")
    count = get_collection_count()
    if count > 0:
        existing_data = collection.get(include=[])
        existing_ids = existing_data.get("ids", [])
        if existing_ids:
            collection.delete(ids=existing_ids)
            print(f"Purged {len(existing_ids)} old chunks from ChromaDB.")
            
    print("Re-indexing raw text documents...")
    chunks = []
    for file_name in os.listdir(RAW_DATA_DIR):
        if file_name.endswith(".txt"):
            file_path = os.path.join(RAW_DATA_DIR, file_name)
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            file_chunks = chunk_by_sections(content, file_name, date_str())
            chunks.extend(file_chunks)
            
    if chunks:
        insert_chunks(chunks)
        print(f"Successfully re-indexed {len(chunks)} chunks.")
    else:
        print("No raw text chunks found to insert.")
        
    # Reinitialize BM25 over loaded corpus
    initialize_bm25()

def date_str():
    from datetime import date
    return date.today().isoformat()

@app.post("/api/query")
async def query_endpoint(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query text cannot be empty.")
        
    try:
        response = process_query(request.query)
        return response
    except Exception as e:
        print(f"Error handling query request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/reindex")
async def force_reindex_endpoint():
    """
    Admin endpoint to force database re-indexing from raw files.
    """
    try:
        reindex_all_documents()
        return {
            "status": "success",
            "message": "Database successfully re-indexed.",
            "database_records": get_collection_count()
        }
    except Exception as e:
        print(f"Error during administrative re-indexing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "database_records": get_collection_count()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=HOST, port=PORT, reload=True)
