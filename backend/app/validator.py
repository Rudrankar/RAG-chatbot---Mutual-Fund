import re
from backend.app.config import GROWW_URLS

def split_into_sentences(text: str) -> list[str]:
    """
    Splits text into sentences using basic punctuation markers.
    """
    # Regex splitting on period, question mark, or exclamation followed by space/end of string
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]

def validate_and_format_response(raw_answer: str, context_url: str = None) -> tuple[str, str]:
    """
    Enforces RAG response formatting rules:
    - Maximum 3 sentences.
    - Exactly one citation URL (from whitelisted Groww URLs).
    
    Returns (formatted_answer, citation_url).
    """
    # 1. Extract URLs from the answer text
    url_pattern = re.compile(r'https?://[^\s)\]]+')
    extracted_urls = url_pattern.findall(raw_answer)
    
    # Clean the answer text from inline URL strings to analyze sentence structure
    cleaned_answer = raw_answer
    for url in extracted_urls:
        cleaned_answer = cleaned_answer.replace(url, "")
    
    # 2. Limit to max 3 sentences
    sentences = split_into_sentences(cleaned_answer)
    if len(sentences) > 3:
        sentences = sentences[:3]
    
    final_text = " ".join(sentences)
    
    # 3. Determine Citation URL
    final_citation = None
    
    # Check extracted URLs against whitelist
    valid_extracted = [url.rstrip('.,;!?') for url in extracted_urls if url.rstrip('.,;!?') in GROWW_URLS]
    
    if len(valid_extracted) == 1:
        final_citation = valid_extracted[0]
    elif len(valid_extracted) > 1:
        # If multiple valid, pick the first one
        final_citation = valid_extracted[0]
    elif context_url in GROWW_URLS:
        # Fallback to the context URL if LLM omitted it
        final_citation = context_url
    else:
        # Final fallback to HDFC mutual fund search portal on Groww if nothing else matches
        final_citation = GROWW_URLS[0]
        
    # Standardize spaces and clean up double periods
    final_text = re.sub(r'\s+', ' ', final_text).strip()
    
    return final_text, final_citation
