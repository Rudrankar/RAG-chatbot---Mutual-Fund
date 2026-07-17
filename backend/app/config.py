import os
from dotenv import load_dotenv

# Base Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from specific .env file location
dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path)
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
CHROMA_DB_DIR = os.path.join(DATA_DIR, "chroma")

# Ensure directories exist
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(CHROMA_DB_DIR, exist_ok=True)

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
HF_API_KEY = os.getenv("HF_API_KEY", "")

# Server Configuration
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
MAX_RPM = int(os.getenv("MAX_RPM", "25"))

# Whitelisted Groww URLs for HDFC Mutual Fund
GROWW_URLS = [
    "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
    "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
]

# Mapping URLs to user-friendly scheme names for internal references
URL_TO_SCHEME_NAME = {
    "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth": "HDFC Mid-Cap Opportunities Fund",
    "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth": "HDFC Flexi Cap Fund",
    "https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth": "HDFC Focused 30 Fund",
    "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth": "HDFC ELSS Tax Saver Fund",
    "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth": "HDFC Large Cap Fund"
}
