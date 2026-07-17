import os
import sys
import time
import requests
from datetime import date
import streamlit as st

# Set page configuration with premium tab titles and icons
st.set_page_config(
    page_title="HDFC Mutual Fund FAQ Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Insert root directory into sys.path to allow importing from backend
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# Custom premium CSS theme styling injected directly
st.markdown(
    """
    <style>
    /* Import Premium Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap');
    
    /* Main App Background Override */
    [data-testid="stAppViewContainer"] {
        background-color: #0B0F19 !important;
        background-image: 
            radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.15) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(16, 185, 129, 0.1) 0px, transparent 50%) !important;
        color: #F3F4F6 !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Block container limits width for chat focus */
    [data-testid="stAppViewBlockContainer"] {
        max-width: 950px !important;
        padding-top: 3rem !important;
        padding-bottom: 5rem !important;
    }
    
    /* Sidebar custom styling */
    [data-testid="stSidebar"] {
        background-color: rgba(17, 24, 39, 0.9) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
    }
    
    /* Font Overrides */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif !important;
        color: #FFFFFF !important;
    }
    
    p, span, div, li {
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Suggestion Chips Overrides */
    div.stButton > button {
        background-color: #171E2E !important;
        color: #F3F4F6 !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 13.5px !important;
        font-weight: 500 !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        text-align: left !important;
        width: 100% !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
    }
    div.stButton > button:hover {
        background-color: rgba(16, 185, 129, 0.08) !important;
        border-color: rgba(16, 185, 129, 0.3) !important;
        color: #10B981 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 0 12px rgba(16, 185, 129, 0.25) !important;
    }
    div.stButton > button:active {
        transform: translateY(0) !important;
    }
    
    /* Native Chat Message Container Overrides */
    [data-testid="stChatMessage"] {
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin-bottom: 0 !important;
        box-shadow: none !important;
    }
    
    [data-testid="stChatMessageAvatarReceived"], [data-testid="stChatMessageAvatarUser"] {
        display: none !important;
    }
    
    /* Custom Chat Bubbles Layout */
    .chat-message-container {
        width: 100%;
        display: flex;
        margin: 12px 0;
        font-family: 'Inter', sans-serif;
    }
    
    .user-container {
        justify-content: flex-end;
    }
    
    .assistant-container {
        justify-content: flex-start;
    }
    
    .user-bubble {
        background-color: #1E293B !important;
        border: 1px solid rgba(13, 148, 136, 0.3) !important;
        color: #FFFFFF !important;
        padding: 12px 18px !important;
        border-radius: 16px 16px 4px 16px !important;
        max-width: 70% !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25) !important;
        word-wrap: break-word;
        font-size: 15px;
        line-height: 1.5;
    }
    
    .assistant-bubble {
        background-color: #171E2E !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        color: #F3F4F6 !important;
        padding: 16px 20px !important;
        border-radius: 16px 16px 16px 4px !important;
        max-width: 75% !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3) !important;
        word-wrap: break-word;
        font-size: 15px;
        line-height: 1.5;
    }
    
    .refusal-bubble {
        background-color: rgba(23, 30, 46, 0.95) !important;
        border: 1px solid rgba(245, 158, 11, 0.3) !important;
        box-shadow: 0 8px 32px 0 rgba(245, 158, 11, 0.05) !important;
    }
    
    .refusal-header {
        font-family: 'Outfit', sans-serif;
        color: #F59E0B;
        font-weight: 700;
        font-size: 14px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    .answer-text {
        margin: 0 !important;
        color: #F3F4F6;
    }
    
    .citation-box {
        margin-top: 12px;
        display: flex;
        align-items: center;
    }
    
    .citation-link {
        background: rgba(16, 185, 129, 0.08) !important;
        border: 1px solid rgba(16, 185, 129, 0.2) !important;
        color: #10B981 !important;
        text-decoration: none !important;
        font-weight: 600 !important;
        font-size: 12px !important;
        padding: 4px 10px !important;
        border-radius: 20px !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
        transition: all 0.2s ease !important;
    }
    
    .citation-link:hover {
        background: rgba(16, 185, 129, 0.18) !important;
        border-color: #10B981 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 0 8px rgba(16, 185, 129, 0.3) !important;
    }
    
    .cta-buttons {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 12px;
    }
    
    .cta-button {
        background: rgba(245, 158, 11, 0.08) !important;
        border: 1px solid rgba(245, 158, 11, 0.2) !important;
        color: #F59E0B !important;
        text-decoration: none !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        padding: 6px 12px !important;
        border-radius: 8px !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 4px !important;
        transition: all 0.2s ease !important;
    }
    
    .cta-button:hover {
        background: rgba(245, 158, 11, 0.18) !important;
        border-color: #F59E0B !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 0 8px rgba(245, 158, 11, 0.3) !important;
    }
    
    .metadata-row {
        display: flex;
        justify-content: space-between;
        margin-top: 12px;
        font-size: 11px;
        color: #9CA3AF;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        padding-top: 8px;
    }
    
    .metadata-item {
        display: flex;
        align-items: center;
        gap: 4px;
    }
    
    /* Native Chat Input Custom Styling */
    [data-testid="stChatInput"] {
        border-radius: 14px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        background-color: rgba(17, 24, 39, 0.8) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37) !important;
        transition: all 0.3s ease !important;
    }
    
    [data-testid="stChatInput"]:focus-within {
        border-color: #10B981 !important;
        box-shadow: 0 0 12px rgba(16, 185, 129, 0.3) !important;
    }
    
    [data-testid="stChatInput"] textarea {
        color: #FFFFFF !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 14.5px !important;
    }
    
    [data-testid="stChatInput"] button {
        background-color: #10B981 !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stChatInput"] button:hover {
        background-color: #059669 !important;
        transform: scale(1.05) !important;
    }
    
    /* Pulse Animations for Skeleton Loader */
    @keyframes pulse {
        0% { opacity: 0.6; }
        50% { opacity: 1; }
        100% { opacity: 0.6; }
    }
    
    .skeleton-line {
        background-color: rgba(255, 255, 255, 0.05);
        height: 14px;
        border-radius: 4px;
        margin-bottom: 8px;
        animation: pulse 1.5s infinite ease-in-out;
    }
    
    .skeleton-title {
        width: 40%;
        height: 16px;
        background-color: rgba(16, 185, 129, 0.15);
    }
    
    .skeleton-text-1 {
        width: 90%;
    }
    
    .skeleton-text-2 {
        width: 75%;
        margin-bottom: 16px;
    }
    
    .skeleton-metadata {
        background-color: rgba(255, 255, 255, 0.03);
        height: 10px;
        width: 30%;
        border-radius: 3px;
        animation: pulse 1.5s infinite ease-in-out;
    }
    
    /* Scheme coverage card styling */
    .scheme-card {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 24px;
    }
    
    /* Welcome Box styles */
    .welcome-box {
        background-color: #171E2E !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border-radius: 16px !important;
        padding: 32px !important;
        max-width: 800px !important;
        margin: 40px auto 24px auto !important;
        text-align: center !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3) !important;
    }
    .welcome-box h2 {
        font-family: 'Outfit', sans-serif !important;
        font-size: 26px !important;
        color: #FFFFFF !important;
        margin-bottom: 12px !important;
        font-weight: 700 !important;
    }
    .welcome-box p {
        font-family: 'Inter', sans-serif !important;
        font-size: 14.5px !important;
        color: #9CA3AF !important;
        line-height: 1.6 !important;
        margin-bottom: 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# API Endpoint definition
DEFAULT_API_URL = "http://127.0.0.1:8000"

def check_api_health(url):
    """
    Pings the health endpoint of the FastAPI server.
    """
    try:
        res = requests.get(f"{url}/api/health", timeout=1.5)
        if res.status_code == 200:
            return True, res.json().get("database_records", 0)
    except Exception:
        pass
    return False, 0

# Sidebar Construction
with st.sidebar:
    # App Logo and Header
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 24px;">
            <span style="font-size: 28px;">📊</span>
            <h2 style="margin: 0; font-weight: 700; letter-spacing: -0.5px; background: linear-gradient(135deg, #FFF 0%, #9CA3AF 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">HDFC FAQ Bot</h2>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Critical Compliance Banner Box
    st.markdown(
        """
        <div style="background: rgba(245, 158, 11, 0.06); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: 12px; padding: 16px; margin-bottom: 24px;">
            <div style="font-family: 'Outfit', sans-serif; font-size: 10px; font-weight: 800; letter-spacing: 1px; color: #F59E0B; background: rgba(245, 158, 11, 0.15); padding: 4px 8px; border-radius: 6px; width: max-content; margin-bottom: 8px;">CRITICAL COMPLIANCE</div>
            <p style="font-size: 13px; line-height: 1.5; color: #FBBF24; margin: 0;"><strong>Facts-only. No investment advice.</strong> This assistant answers verified, objective questions exclusively from official scheme parameters.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # API Health Status Indicator
    is_online, db_count = check_api_health(DEFAULT_API_URL)
    
    if is_online:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 8px; font-size: 13px; margin-bottom: 24px; color: #10B981; font-weight: 600;">
                <span style="height: 10px; width: 10px; background-color: #10B981; border-radius: 50%; display: inline-block;"></span>
                FastAPI Server: ONLINE ({db_count} chunks)
            </div>
            """,
            unsafe_allow_html=True
        )
        use_fallback = False
    else:
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 8px; font-size: 13px; margin-bottom: 24px; color: #F59E0B; font-weight: 600;">
                <span style="height: 10px; width: 10px; background-color: #F59E0B; border-radius: 50%; display: inline-block;"></span>
                FastAPI Server: OFFLINE (Direct Fallback Active)
            </div>
            """,
            unsafe_allow_html=True
        )
        use_fallback = True

    # Whitelisted Schemes Listing inside a styled card
    st.markdown(
        """
        <div class="scheme-card">
            <h3 style="font-family: 'Outfit', sans-serif; font-size: 14px; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 0; margin-bottom: 12px;">Indexed Schemes</h3>
            <ul style="list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px;">
                <li style="font-size: 13px; color: #F3F4F6; padding-left: 12px; border-left: 2px solid #3B82F6; line-height: 1.4;">HDFC Mid-Cap Opportunities Fund</li>
                <li style="font-size: 13px; color: #F3F4F6; padding-left: 12px; border-left: 2px solid #3B82F6; line-height: 1.4;">HDFC Flexi Cap Fund</li>
                <li style="font-size: 13px; color: #F3F4F6; padding-left: 12px; border-left: 2px solid #3B82F6; line-height: 1.4;">HDFC Focused 30 Fund</li>
                <li style="font-size: 13px; color: #F3F4F6; padding-left: 12px; border-left: 2px solid #3B82F6; line-height: 1.4;">HDFC ELSS Tax Saver Fund</li>
                <li style="font-size: 13px; color: #F3F4F6; padding-left: 12px; border-left: 2px solid #3B82F6; line-height: 1.4;">HDFC Large Cap Fund</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown(
        """
        <div style="margin-top: auto; padding-top: 40px; font-size: 11px; color: #9CA3AF; border-top: 1px solid rgba(255, 255, 255, 0.05);">
            <p style="margin: 0 0 4px 0;">System Version 1.0.0</p>
            <p style="margin: 0;">Source Data: groww.in</p>
        </div>
        """,
        unsafe_allow_html=True
    )

# Session State Initializations
if "messages" not in st.session_state:
    st.session_state.messages = []

if "chip_query" not in st.session_state:
    st.session_state.chip_query = None

def get_friendly_domain(url):
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return "groww.in"

def run_query(query):
    """
    Executes the query via FastAPI HTTP call, falling back to direct package import if server is offline.
    """
    if not use_fallback:
        try:
            res = requests.post(f"{DEFAULT_API_URL}/api/query", json={"query": query}, timeout=15)
            if res.status_code == 200:
                return res.json()
        except Exception:
            pass
            
    # Direct Fallback Import Mode
    try:
        # Import components directly
        from backend.app.orchestrator import process_query
        from backend.app.database import get_collection_count
        
        # Double check database is initialized
        if get_collection_count() == 0:
            from backend.app.main import startup_db_check
            startup_db_check()
                
        return process_query(query)
    except Exception as e:
        return {
            "query": query,
            "answer": f"System Error: Offline execution fallback failed. Details: {e}",
            "citation_url": "https://www.amfiindia.com/investor-corner",
            "last_updated": date.today().isoformat(),
            "is_refusal": True,
            "execution_time_ms": 0
        }

# Main Panel Layout
# If no messages exist, display welcome box & suggestion grid
if not st.session_state.messages:
    st.markdown(
        """
        <div class="welcome-box">
            <h2>Welcome to the HDFC Mutual Fund FAQ Assistant 👋</h2>
            <p>
                I can help you retrieve factual parameters about 5 indexed HDFC mutual fund schemes. Please click one of the example queries below or write your own objective question.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Display Suggestion Grid (3 columns)
    grid_cols = st.columns(3)
    
    with grid_cols[0]:
        if st.button("📋 What is the exit load for HDFC Mid Cap?"):
            st.session_state.chip_query = "What is the exit load for the HDFC Mid Cap Fund?"
            st.rerun()
            
    with grid_cols[1]:
        if st.button("💰 Minimum SIP for HDFC ELSS?"):
            st.session_state.chip_query = "What is the minimum SIP for the HDFC ELSS Tax Saver?"
            st.rerun()
            
    with grid_cols[2]:
        if st.button("⚠️ Should I invest in HDFC Large Cap?"):
            st.session_state.chip_query = "Should I invest in HDFC Large Cap Fund?"
            st.rerun()

# Render chat messages from history using custom premium HTML templates
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f"""
            <div class="chat-message-container user-container">
                <div class="user-bubble">
                    {msg["content"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        is_refusal = msg.get("is_refusal", False)
        answer = msg["content"]
        citation_url = msg.get("citation_url")
        last_updated = msg.get("last_updated")
        latency = msg.get("latency_ms", 120)
        
        if is_refusal:
            # Render refusal bubble
            # We determine if it is an advisory refusal or a general compliance guardrail
            heading = "⚠️ Advisory Refusal" if "advice" in answer.lower() or "invest" in answer.lower() else "🔒 Compliance Guardrail"
            
            st.markdown(
                f"""
                <div class="chat-message-container assistant-container">
                    <div class="assistant-bubble refusal-bubble">
                        <div class="refusal-header">
                            <span>{heading[:2]}</span> {heading[2:]}
                        </div>
                        <p class="answer-text">{answer}</p>
                        <div class="cta-buttons">
                            <a class="cta-button" href="https://www.amfiindia.com/investor-corner" target="_blank" rel="noopener noreferrer">AMFI Investor Corner ↗</a>
                            <a class="cta-button" href="https://www.investor.sebi.gov.in" target="_blank" rel="noopener noreferrer">SEBI Investor Education ↗</a>
                        </div>
                        <div class="metadata-row">
                            <span class="metadata-item">📅 Last Updated: {last_updated}</span>
                            <span class="metadata-item">⚡ {latency}ms</span>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            # Render factual response bubble
            friendly_domain = get_friendly_domain(citation_url) if citation_url else "groww.in"
            citation_html = ""
            if citation_url:
                citation_html = f"""
                <div class="citation-box">
                    <a class="citation-link" href="{citation_url}" target="_blank" rel="noopener noreferrer">
                        <span>🔗</span> Source: {friendly_domain} <span class="citation-arrow">↗</span>
                    </a>
                </div>
                """
            
            st.markdown(
                f"""
                <div class="chat-message-container assistant-container">
                    <div class="assistant-bubble">
                        <p class="answer-text">{answer}</p>
                        {citation_html}
                        <div class="metadata-row">
                            <span class="metadata-item">📅 Last Updated: {last_updated}</span>
                            <span class="metadata-item">⚡ {latency}ms</span>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

# Accept input either from Chat Input or from suggestion chips
chat_input = st.chat_input("Ask about exit loads, minimum SIPs, expense ratios...")

target_query = None
if chat_input:
    target_query = chat_input
elif st.session_state.chip_query:
    target_query = st.session_state.chip_query
    st.session_state.chip_query = None  # Reset state

if target_query:
    # Render user query immediately
    st.session_state.messages.append({"role": "user", "content": target_query})
    st.markdown(
        f"""
        <div class="chat-message-container user-container">
            <div class="user-bubble">
                {target_query}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
        
    # Render bot loading state with pulsing skeleton screen loader and run query
    placeholder = st.empty()
    placeholder.markdown(
        """
        <div class="chat-message-container assistant-container">
            <div class="assistant-bubble" style="width: 100%;">
                <div class="skeleton-line skeleton-title"></div>
                <div class="skeleton-line skeleton-text-1"></div>
                <div class="skeleton-line skeleton-text-2"></div>
                <div class="skeleton-metadata"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    result = run_query(target_query)
    
    # Clear loading skeleton
    placeholder.empty()
    
    answer = result.get("answer", "No answer generated.")
    is_refusal = result.get("is_refusal", False)
    citation_url = result.get("citation_url")
    last_updated = result.get("last_updated")
    latency_ms = result.get("execution_time_ms", 120)
    
    # Save Assistant Response to Session History
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "is_refusal": is_refusal,
        "citation_url": citation_url,
        "last_updated": last_updated,
        "latency_ms": latency_ms
    })
    
    st.rerun()
