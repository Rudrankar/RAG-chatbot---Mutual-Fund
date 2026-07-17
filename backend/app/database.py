import os
import json
import re
import requests
import chromadb
from rank_bm25 import BM25Okapi
from backend.app.config import DATA_DIR, CHROMA_DB_DIR, OPENAI_API_KEY, GEMINI_API_KEY, HF_API_KEY

# Global variables for BM25
bm25_instance = None
bm25_documents = []

# Initialize ChromaDB Client
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
collection = chroma_client.get_or_create_collection(name="mutual_fund_faq")

def tokenize(text):
    return re.findall(r'\w+', text.lower())

def get_embedding(text: str, is_query: bool = False) -> list[float]:
    """
    Retrieves embedding vectors using BGE Model (via HF API) as preferred choice, 
    with OpenAI or Gemini REST APIs and character hashes as fallback.
    """
    # 1. BGE Model (via Hugging Face Inference API)
    try:
        url = "https://api-inference.huggingface.co/pipeline/feature-extraction/BAAI/bge-small-en-v1.5"
        headers = {}
        if HF_API_KEY:
            headers["Authorization"] = f"Bearer {HF_API_KEY}"
        
        # Prepend query instruction for asymmetric BGE search
        input_text = text
        if is_query:
            input_text = f"Represent this sentence for searching relevant passages: {text}"
            
        res = requests.post(url, headers=headers, json={"inputs": input_text}, timeout=8)
        if res.status_code == 200:
            embedding = res.json()
            if isinstance(embedding, list) and len(embedding) > 0:
                if isinstance(embedding[0], float):
                    return embedding
                elif isinstance(embedding[0], list):
                    return embedding[0]
    except Exception as e:
        print(f"BGE embedding extraction failed: {e}")

    # 2. OpenAI Embeddings (Fallback)
    if OPENAI_API_KEY:
        try:
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "input": text,
                "model": "text-embedding-3-small"
            }
            res = requests.post("https://api.openai.com/v1/embeddings", headers=headers, json=payload, timeout=8)
            if res.status_code == 200:
                return res.json()["data"][0]["embedding"]
        except Exception as e:
            print(f"OpenAI embedding fallback failed: {e}")

    # 3. Gemini Embeddings (Fallback)
    if GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={GEMINI_API_KEY}"
            payload = {
                "content": {
                    "parts": [{"text": text}]
                }
            }
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                return res.json()["embedding"]["values"]
        except Exception as e:
            print(f"Gemini embedding fallback failed: {e}")

    # 4. Deterministic Local Hash Fallback (No APIs)
    vector = [0.0] * 384
    clean_text = text.lower()
    for i in range(len(clean_text)):
        idx = (i + ord(clean_text[i])) % 384
        vector[idx] += 1.0
    norm = sum(x*x for x in vector) ** 0.5
    if norm > 0:
        vector = [x/norm for x in vector]
    return vector

def initialize_bm25():
    global bm25_instance, bm25_documents
    
    count = get_collection_count()
    if count == 0:
        bm25_instance = None
        bm25_documents = []
        return
        
    # Get all documents from ChromaDB
    data = collection.get(include=["documents", "metadatas"])
    ids = data.get("ids", [])
    documents = data.get("documents", [])
    metadatas = data.get("metadatas", [])
    
    bm25_documents = []
    corpus_tokens = []
    for doc, meta in zip(documents, metadatas):
        bm25_documents.append({"text": doc, "metadata": meta})
        corpus_tokens.append(tokenize(doc))
        
    if corpus_tokens:
        bm25_instance = BM25Okapi(corpus_tokens)
        print(f"BM25 initialized with {len(bm25_documents)} documents from ChromaDB.")
    else:
        bm25_instance = None
        bm25_documents = []

def insert_chunks(chunks):
    """
    chunks: list of dicts: {"id": str, "text": str, "metadata": dict}
    """
    if not chunks:
        return
        
    # Get all existing IDs in the collection
    existing_data = collection.get(include=[])
    existing_ids = set(existing_data.get("ids", []))
    
    new_ids = []
    new_embeddings = []
    new_documents = []
    new_metadatas = []
    
    print(f"Checking {len(chunks)} chunks against ChromaDB...")
    for idx, c in enumerate(chunks, 1):
        if c["id"] in existing_ids:
            continue
            
        emb = get_embedding(c["text"])
        new_ids.append(c["id"])
        new_embeddings.append(emb)
        new_documents.append(c["text"])
        new_metadatas.append(c["metadata"])
        
        if idx % 5 == 0:
            print(f"Embedded {idx}/{len(chunks)} chunks.")
            
    if new_ids:
        collection.add(
            ids=new_ids,
            embeddings=new_embeddings,
            documents=new_documents,
            metadatas=new_metadatas
        )
        print(f"Successfully added {len(new_ids)} new chunks to ChromaDB.")
    else:
        print("No new chunks to add to ChromaDB.")
        
    # Reinitialize BM25 over the updated database
    initialize_bm25()

def get_collection_count():
    return collection.count()

def cosine_similarity(v1, v2):
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = sum(a * a for a in v1) ** 0.5
    norm_v2 = sum(b * b for b in v2) ** 0.5
    if norm_v1 * norm_v2 == 0.0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)

def hybrid_retrieve(query_text, k=3):
    """
    Performs custom dense semantic search via ChromaDB + sparse BM25 search, fusing results using RRF.
    Filters retrieval candidates by target scheme detection to avoid cross-fund context contamination.
    """
    global bm25_instance, bm25_documents
    
    count = get_collection_count()
    if count == 0:
        return []
        
    # 1. Detect target scheme keywords
    query_lower = query_text.lower()
    target_kw = None
    
    if any(kw in query_lower for kw in ["mid cap", "mid-cap", "midcap"]):
        target_kw = "mid"
    elif any(kw in query_lower for kw in ["flexi cap", "flexicap", "equity"]):
        target_kw = "flexi"
    elif "focused" in query_lower:
        target_kw = "focused"
    elif any(kw in query_lower for kw in ["elss", "tax saver", "tax-saver"]):
        target_kw = "elss"
    elif any(kw in query_lower for kw in ["large cap", "largecap"]):
        target_kw = "large"
        
    def matches_scheme(doc_meta):
        if not target_kw:
            return True
        scheme_name = doc_meta.get("scheme_name", "").lower()
        return target_kw in scheme_name

    # 2. Dense Search (ChromaDB query)
    query_emb = get_embedding(query_text, is_query=True)
    # Query with a larger candidate count to ensure we get enough matching scheme chunks
    n_results = min(50, count)
    
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=n_results,
        include=["documents", "metadatas"]
    )
    
    dense_results = []
    if results and "documents" in results and results["documents"] and results["documents"][0]:
        for doc_text, meta in zip(results["documents"][0], results["metadatas"][0]):
            if matches_scheme(meta):
                dense_results.append({"text": doc_text, "metadata": meta})
                
    # Take top 10 matching dense candidates
    dense_candidates = dense_results[:10]
            
    # 3. Sparse Search (Dynamic Scheme-Aware BM25)
    bm25_candidates = []
    filtered_bm25_docs = [doc for doc in bm25_documents if matches_scheme(doc["metadata"])]
    
    if filtered_bm25_docs:
        corpus_tokens = [tokenize(doc["text"]) for doc in filtered_bm25_docs]
        temp_bm25 = BM25Okapi(corpus_tokens)
        query_tokens = tokenize(query_text)
        scores = temp_bm25.get_scores(query_tokens)
        sorted_indices = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)
        for idx in sorted_indices[:10]:
            if scores[idx] > 0.0:
                bm25_candidates.append(filtered_bm25_docs[idx])
                
    # 4. Reciprocal Rank Fusion (RRF)
    rrf_scores = {}
    doc_mapping = {}
    
    def add_ranks(results_list):
        for rank, doc in enumerate(results_list):
            key = (doc["text"], doc["metadata"].get("source_url", ""))
            doc_mapping[key] = doc
            if key not in rrf_scores:
                rrf_scores[key] = 0.0
            rrf_scores[key] += 1.0 / (60.0 + (rank + 1))
            
    add_ranks(dense_candidates)
    add_ranks(bm25_candidates)
    
    sorted_keys = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)
    merged_results = [doc_mapping[key] for key in sorted_keys[:k]]
    
    if not merged_results and dense_candidates:
        merged_results = dense_candidates[:k]
        
    return merged_results

# Load database and BM25 index on start
try:
    initialize_bm25()
except Exception as e:
    print(f"Error loading ChromaDB on startup: {e}")
