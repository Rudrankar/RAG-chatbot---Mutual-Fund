import os
import time
from datetime import date
from backend.app.config import OPENAI_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, URL_TO_SCHEME_NAME
from backend.app.database import hybrid_retrieve
from backend.app.guardrails import scan_pii, check_intent
from backend.app.validator import validate_and_format_response

# Standard Refusal Links
AMFI_URL = "https://www.amfiindia.com/investor-corner"
SEBI_URL = "https://www.investor.sebi.gov.in"

def run_local_fallback(query: str, retrieved_chunks: list) -> str:
    """
    Fallback answer generator when no LLM API keys are present.
    Determines exit load, expense ratio, or statement download instructions based on keyword matching.
    """
    if not retrieved_chunks:
        return "I am sorry, but I could not retrieve any context matching your query. Please specify a whitelisted scheme name."

    # Inspect the top retrieved document
    top_doc = retrieved_chunks[0]["text"]
    lines = top_doc.split("\n")
    query_lower = query.lower()

    # Find the most relevant lines
    matched_lines = []
    
    # 1. Statement download query
    if "statement" in query_lower or "download" in query_lower or "report" in query_lower:
        for line in lines:
            if "statement" in line.lower() or "report" in line.lower() or "download" in line.lower():
                matched_lines.append(line)
                
    # 2. Riskometer query
    elif "riskometer" in query_lower or "risk" in query_lower:
        for line in lines:
            if "riskometer" in line.lower() or "risk" in line.lower():
                matched_lines.append(line)
                
    # 3. Exit load query
    elif "exit load" in query_lower or "exit" in query_lower or "load" in query_lower:
        for line in lines:
            if "exit load" in line.lower() or "redeemed" in line.lower():
                matched_lines.append(line)
                
    # 4. Expense ratio query
    elif "expense" in query_lower or "ratio" in query_lower or "ter" in query_lower:
        for line in lines:
            if "expense" in line.lower() or "ratio" in line.lower() or "ter" in line.lower():
                matched_lines.append(line)
                
    # 5. Lock-in query
    elif "lock" in query_lower or "elss" in query_lower:
        for line in lines:
            if "lock" in line.lower() or "elss" in line.lower():
                matched_lines.append(line)

    # Clean matched lines
    clean_matches = [l.strip("- ").strip() for l in matched_lines if l.strip()]
    
    if clean_matches:
        # Construct a simple answer from matches
        text = " ".join(clean_matches[:2])
        # Ensure it has a full stop
        if not text.endswith("."):
            text += "."
        return f"Based on retrieved offline source details: {text}"
    
    # Generic fallback: summarize key statistics
    stats = []
    for line in lines:
        if line.strip().startswith("-") or "Ratio" in line or "Load" in line or "SIP" in line:
            stats.append(line.strip("- ").strip())
    
    if stats:
        text = " ".join(stats[:2])
        return f"Retrieved metrics: {text}."
        
    return "The HDFC mutual fund scheme documentation contains facts answering this query, but an active LLM API key is required to synthesize the full answer text."

def get_llm_response(prompt: str) -> str:
    """
    Queries Groq API (primary model), falling back to Gemini or OpenAI depending on configured keys.
    Implements exponential backoff on HTTP 429 rate limiting.
    """
    import requests
    
    # 1. Groq API (Primary LLM Core)
    if GROQ_API_KEY:
        delays = [1.0, 2.0, 4.0] # retry delays for rate limits
        for attempt, delay in enumerate(delays + [0]):
            try:
                headers = {
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0
                }
                res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=10)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"].strip()
                elif res.status_code == 429:
                    # Rate limit exceeded. Apply backoff if we have remaining retries.
                    if attempt < len(delays):
                        print(f"Groq API rate limit (429) hit. Retrying in {delay}s...")
                        time.sleep(delay)
                        continue
                    else:
                        print("Groq API rate limit retries exhausted. Checking fallbacks...")
                else:
                    print(f"Groq API returned HTTP {res.status_code}: {res.text}. Checking fallbacks...")
                    break
            except Exception as e:
                print(f"Groq API execution failed: {e}. Checking fallbacks...")
                break

    # 2. Gemini API (Fallback)
    if GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0
                )
            )
            return response.text.strip()
        except Exception as e:
            print(f"Gemini API fallback failed: {e}. Checking OpenAI fallback...")

    # 3. OpenAI API (Fallback)
    if OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI API fallback failed: {e}.")
            
    return ""

# Simple cache to save token budget on duplicate queries
query_cache = {}
CACHE_TTL = 3600 # 1 hour

def process_query(query: str) -> dict:
    """
    Coordinates RAG operations: Guardrails -> Retrieval -> Grounded Generation -> Output Validation.
    """
    start_time = time.time()
    today = date.today().isoformat()
    
    # Simple cache check
    cache_key = query.strip().lower()
    if cache_key in query_cache:
        cached_entry = query_cache[cache_key]
        if time.time() - cached_entry["timestamp"] < CACHE_TTL:
            res = cached_entry["result"].copy()
            res["execution_time_ms"] = int((time.time() - start_time) * 1000)
            return res
    
    # 1. Input Guardrail: PII Scan
    has_pii, pii_message = scan_pii(query)
    if has_pii:
        return {
            "query": query,
            "answer": f"Warning: {pii_message} As a security precaution, this transaction cannot be completed.",
            "citation_url": AMFI_URL,
            "last_updated": today,
            "is_refusal": True,
            "execution_time_ms": int((time.time() - start_time) * 1000)
        }
        
    # 2. Input Guardrail: Intent Check (Advisory & Comparison rejection)
    is_advisory, explanation = check_intent(query)
    if is_advisory:
        return {
            "query": query,
            "answer": "As a facts-only assistant, I am unable to provide investment advice, comparison ratings, opinions, or recommendations on fund selections. Please consult SEBI or AMFI documentation for financial planning.",
            "citation_url": SEBI_URL,
            "last_updated": today,
            "is_refusal": True,
            "execution_time_ms": int((time.time() - start_time) * 1000)
        }

    # 3. Retrieval
    retrieved = hybrid_retrieve(query, k=3)
    context_text = ""
    context_url = None
    
    if retrieved:
        # Build context prompt layout
        contexts = []
        for i, doc in enumerate(retrieved):
            contexts.append(f"Context [{i+1}]:\nSource URL: {doc['metadata'].get('source_url')}\nContent: {doc['text']}")
        context_text = "\n\n".join(contexts)
        context_url = retrieved[0]["metadata"].get("source_url")
        
    # 4. Generate Answer
    raw_answer = ""
    if context_text:
        system_prompt = (
            f"You are a factual Mutual Fund FAQ Assistant for HDFC mutual fund schemes.\n"
            f"Answer the user query strictly using details from the Context below. Do not assume or extrapolate.\n\n"
            f"Context details:\n{context_text}\n\n"
            f"Rules:\n"
            f"1. Keep the answer factual, objective, and short (1 to 3 sentences maximum).\n"
            f"2. Never provide investment advice, fund recommendations, or opinion rankings.\n"
            f"3. Include the matching Source URL citation link exactly once in your response.\n"
            f"4. If the Context does not contain the answer, reply with: 'I am sorry, but the documentation does not contain this information.'\n\n"
            f"Query: {query}\n"
            f"Answer:"
        )
        raw_answer = get_llm_response(system_prompt)
        
    # Fallback to local regex-based parsing if no LLM responded
    if not raw_answer:
        raw_answer = run_local_fallback(query, retrieved)
        
    # 5. Output Validation
    formatted_answer, citation = validate_and_format_response(raw_answer, context_url)
    
    # 6. Format check if LLM returned a default out-of-bounds rejection message
    is_not_found = "does not contain this information" in formatted_answer or "could not retrieve" in formatted_answer
    
    response_dict = {
        "query": query,
        "answer": formatted_answer,
        "citation_url": citation if citation else AMFI_URL,
        "last_updated": today,
        "is_refusal": is_not_found,
        "execution_time_ms": int((time.time() - start_time) * 1000)
    }
    
    # Cache the result (don't cache refusals or guardrail rejections to allow retry/updated documents)
    if not is_not_found:
        query_cache[cache_key] = {
            "result": response_dict,
            "timestamp": time.time()
        }
        
    return response_dict
