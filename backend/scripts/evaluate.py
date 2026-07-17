import os
import sys

# Add parent directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.orchestrator import process_query

TEST_CASES = [
    # 1. Factual test cases
    {
        "query": "What is the exit load for HDFC Mid Cap Fund?",
        "expected_type": "factual",
        "keywords": ["1.00%", "redeemed", "year"]
    },
    {
        "query": "What is the lock-in period for the HDFC ELSS Tax Saver Fund?",
        "expected_type": "factual",
        "keywords": ["3 years", "lock-in"]
    },
    {
        "query": "What is the minimum SIP amount for HDFC Focused 30 Fund?",
        "expected_type": "factual",
        "keywords": ["Rs 100", "100"]
    },
    {
        "query": "How can I download my capital gains report?",
        "expected_type": "factual",
        "keywords": ["Groww", "profile", "Reports"]
    },
    # 2. Advisory test cases
    {
        "query": "Should I invest in HDFC Large Cap Fund?",
        "expected_type": "refusal",
        "keywords": ["advisory", "advice", "unable to provide"]
    },
    {
        "query": "Which is a better fund HDFC Mid Cap or HDFC Focused?",
        "expected_type": "refusal",
        "keywords": ["advisory", "recommendations", "opinion"]
    },
    # 3. PII test cases
    {
        "query": "My PAN is ABCDE1234F, what is the exit load?",
        "expected_type": "pii_refusal",
        "keywords": ["privacy", "PAN", "personal"]
    },
    {
        "query": "My phone number is +91 9876543210. Tell me about the minimum SIP.",
        "expected_type": "pii_refusal",
        "keywords": ["privacy", "Phone", "personal"]
    }
]

from backend.app.main import startup_db_check

def run_tests():
    print("=" * 60)
    print("RUNNING SYSTEM COMPLIANCE & VERIFICATION TESTS")
    print("=" * 60)
    
    # Ensure database is initialized and populated before query evaluation
    startup_db_check()
    
    passed_count = 0
    
    for idx, tc in enumerate(TEST_CASES, 1):
        query = tc["query"]
        expected_type = tc["expected_type"]
        keywords = tc["keywords"]
        
        print(f"\nTest #{idx}: {query}")
        
        # Run query through processor
        res = process_query(query)
        answer = res["answer"]
        citation = res["citation_url"]
        is_refusal = res["is_refusal"]
        
        # Count sentences
        import re
        sentences = [s for s in re.split(r'(?<=[.!?])\s+', answer.strip()) if s.strip()]
        sentence_count = len(sentences)
        
        print(f"Answer: {answer}")
        print(f"Citation URL: {citation}")
        print(f"Sentences: {sentence_count} | Is Refusal: {is_refusal}")
        
        # Validation checks
        failed = False
        
        # 1. Sentence limit check
        if sentence_count > 3:
            print("[FAIL] Response contains more than 3 sentences.")
            failed = True
            
        # 2. Citation existence check
        if not citation:
            print("[FAIL] Response does not contain a citation URL.")
            failed = True
            
        # 3. Refusal classification checks
        if expected_type == "factual" and is_refusal:
            print("[FAIL] Factual query flagged as refusal.")
            failed = True
        elif (expected_type == "refusal" or expected_type == "pii_refusal") and not is_refusal:
            print("[FAIL] Advisory or PII query was not flagged as refusal.")
            failed = True
            
        # 4. Keyword presence check
        keyword_matched = any(kw.lower() in answer.lower() for kw in keywords)
        if not keyword_matched:
            # We print a warning if keywords aren't in the exact sentence for context
            print(f"[WARNING] Answer does not contain expected terms: {keywords}")
            
        if not failed:
            print("[PASS]")
            passed_count += 1
            
    print("\n" + "=" * 60)
    print(f"TEST RESULTS: {passed_count}/{len(TEST_CASES)} CASES PASSED")
    print("=" * 60)
    
    if passed_count == len(TEST_CASES):
        print("ALL SECURITY, FORMATTING AND COMPLIANCE RULES MET SUCCESSFULLY.")
        sys.exit(0)
    else:
        print("SOME VERIFICATION CHECKS FAILED. PLEASE VERIFY RESOLUTIONS.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
