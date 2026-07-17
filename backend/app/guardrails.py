import re

# Regex patterns for PII scanning
PAN_PATTERN = re.compile(r'[a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}')
AADHAAR_PATTERN = re.compile(r'\b[2-9]{1}[0-9]{3}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b')
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PHONE_PATTERN = re.compile(r'\b(?:\+?91[-\s]?)?[6-9]\d{9}\b')
OTP_PATTERN = re.compile(r'\b\d{4,6}\b.*\botp\b|\botp\b.*\b\d{4,6}\b', re.IGNORECASE)
ACCOUNT_NO_PATTERN = re.compile(r'\b\d{9,18}\b') # Standard Indian bank account numbers

def scan_pii(query: str) -> tuple[bool, str]:
    """
    Scans query for PII elements like PAN, Aadhaar, Email, Phone, OTP, Account Number.
    Returns (contains_pii, detection_message).
    """
    if PAN_PATTERN.search(query):
        return True, "PAN Card Number details detected. Please do not share tax or identification details."
    
    if AADHAAR_PATTERN.search(query):
        return True, "Aadhaar Card Number details detected. Please do not share government identification numbers."
        
    if EMAIL_PATTERN.search(query):
        return True, "Email Address detected. Please do not share personal contact details."
        
    if PHONE_PATTERN.search(query):
        return True, "Phone Number details detected. Please do not share personal contact details."
        
    if OTP_PATTERN.search(query):
        return True, "One-Time Password (OTP) sequence detected. Please keep verification keys private."
        
    if ACCOUNT_NO_PATTERN.search(query):
        # We check if account or bank terms are nearby to reduce false positives on standard numbers
        if any(term in query.lower() for term in ["bank", "account", "ac", "a/c", "number", "no", "balance"]):
            return True, "Bank Account Number details detected. Please do not share payment details."
            
    return False, ""

# Rule-based advisory and comparison keywords
ADVISORY_KEYWORDS = [
    "should i invest", "should i buy", "which is better", "recommend", "advice",
    "best fund", "is it good", "is it bad", "top rated", "performances comparison",
    "suggest a fund", "which one to choose", "where to invest", "financial advice",
    "market prediction", "future returns", "worth buying", "good to buy",
    "better", "best", "compare", "comparison"
]

def check_intent(query: str) -> tuple[bool, str]:
    """
    Checks if the user's query is asking for advisory or comparison content.
    Returns (is_advisory, explanation).
    """
    clean_query = query.lower().strip()
    
    # 1. Check for explicit keywords
    for keyword in ADVISORY_KEYWORDS:
        if keyword in clean_query:
            return True, f"Subjective/advisory query detected via trigger word: '{keyword}'."
            
    # 2. Check for subjective sentence starters
    subjective_starters = [
        "should i", "which fund is", "which fund should", "why should i",
        "which is the best", "is it advisable", "give me recommendations"
    ]
    for starter in subjective_starters:
        if clean_query.startswith(starter):
            return True, f"Subjective query structure detected starting with: '{starter}'."
            
    return False, ""
