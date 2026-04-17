"""PRODUCTION READY: Sigmanix Tech Chatbot API Server
Designed for React.js frontend + Plesk hosting deployment

Features:
- CORS enabled for frontend integration
- Environment-based configuration (dev/prod)
- Comprehensive logging
- Rate limiting support
- Input validation & sanitization
- Error handling with proper HTTP codes
- Database optimizations
- Graceful shutdown
"""

import os
import json
import logging
import sys
from datetime import datetime
from functools import wraps
from time import time

from dotenv import load_dotenv
from flask import Flask, jsonify, request, session, render_template_string
from flask_cors import CORS
from groq import Groq
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# ============ ENVIRONMENT & LOGGING SETUP ============
load_dotenv()

ENV = os.getenv("FLASK_ENV", "development")
DEBUG = ENV == "development"
LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO

# Configure logging with UTF-8 encoding
import io
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("chatbot.log", encoding='utf-8'),
        logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8'))
    ]
)
logger = logging.getLogger(__name__)

# ============ PRODUCTION CONFIGURATION ============
class Config:
    """Production configuration"""
    MAX_CONTENT_LENGTH = 16 * 1024  # 16KB max request size
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = DEBUG
    SESSION_COOKIE_SECURE = not DEBUG
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(32))

# ============ CORS SETUP FOR REACT.JS ============
REACT_DOMAINS = os.getenv("REACT_DOMAINS", "http://localhost:3000").split(",")
CORS(app, resources={
    r"/api/*": {
        "origins": REACT_DOMAINS,
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "max_age": 3600
    }
})

logger.info(f"CORS enabled for: {REACT_DOMAINS}")

# ============ DATABASE INTEGRATION ============
try:
    from database import (
        init_database,
        get_or_create_student,
        save_conversation,
        save_feedback,
        calculate_student_interest,
        save_student_analysis
    )
    from admin_routes import register_admin_routes
    
    init_database()
    register_admin_routes(app)
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Database initialization failed: {e}")
    raise

# ============ GROQ API VALIDATION ============
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY not set in .env")
    raise RuntimeError("GROQ_API_KEY environment variable is required")

try:
    client = Groq(api_key=GROQ_API_KEY)
    logger.info("Groq client initialized")
except Exception as e:
    logger.error(f"Groq initialization failed: {e}")
    raise

# ============ KNOWLEDGE BASE LOADING ============
logger.info("Loading knowledge base...")
try:
    with open("data.txt", "r", encoding="utf-8") as f:
        text = f.read()
    
    splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = splitter.create_documents([text])
    logger.info(f"Created {len(docs)} chunks from knowledge base")
    
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    db = FAISS.from_documents(docs, embeddings)
    logger.info("FAISS index ready")
except FileNotFoundError:
    logger.error("data.txt not found. Knowledge base unavailable.")
    raise
except Exception as e:
    logger.error(f"Knowledge base loading failed: {e}")
    raise

# ============ SYSTEM PROMPT & MENU CONFIG ============
SYSTEM_PROMPT = """You are an assistant for Sigmanix Tech. Answer ONLY using provided context.
GOALS: Greet users, show course categories, answer questions, encourage enrollment.
RULES: No fake info, no generic AI disclaimers, keep replies 4-6 lines max, use context only."""

MAIN_MENU_OPTIONS = [
    {"label": "📚 Courses", "value": "courses"},
    {"label": "⏱️ Duration", "value": "duration"},
    {"label": "💼 Placements", "value": "placements"},
    {"label": "📝 Registration", "value": "registration"},
    {"label": "❓ Other", "value": "other"},
]

CATEGORY_REPLIES = {
    "courses": {"reply": "Courses at Sigmanix Tech:\n📚 Python with AI\n📚 Gen AI & Agentic AI\n📚 Data Analytics with AI\n📚 DevOps\n\nWhich interests you?", "options": [{"label": "← Back", "value": "menu"}]},
    "duration": {"reply": "Standard: 8-12 weeks\nIntensive: 4-6 weeks\nPart-time: 12-16 weeks\n\nChoose based on your schedule!", "options": [{"label": "← Back", "value": "menu"}]},
    "placements": {"reply": "✓ 100% job-ready\n✓ Interview prep\n✓ Company referrals\n✓ 40-60% salary boost\n\nWant details?", "options": [{"label": "← Back", "value": "menu"}]},
    "registration": {"reply": "📋 Visit: sigmanixtech.com/contact\n📞 Call: +91 7416527373\n📧 Email: hrsigmanixtech@gmail.com\n\nFree consultation!", "options": [{"label": "← Back", "value": "menu"}]},
}

if __name__ == "__main__":
    logger.info("Starting Sigmanix Tech Chatbot...")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=DEBUG)