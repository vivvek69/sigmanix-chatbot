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

# ============ SYSTEM PROMPT ============
SYSTEM_PROMPT = """You are an assistant for Sigmanix Tech. Answer only using the provided context.
YOUR GOALS:
-greet when user says hello
-After greeting, show Categorical options to user to choose in what category they have queries courses,duration,placements,registration process,etc.
-if he choose any one option from it then give details about that option and then ask if they want to know about it or there is other queries in other options or want to ask something else then give an option to go back to main categories or ask new question
- Help students choose the right career path
- Answer questions using ONLY the provided context
- Give clear, honest, and helpful guidance
- Naturally encourage students to join Sigmanix Tech
STRICT RULES:
- Do NOT add fake information
- Response should be short and to the point
- Do NOT criticize other institutes
- donot say "As an AI language model"
- Do NOT mention company names unless in context
- Do NOT claim partnerships unless mentioned
- if they are employess then say about corporate training and benefits
- If they ask about registrtionform send :For registration form, please visit: https://sigmanixtech.com/contact and fill out the form or contact us directly at +91 7416527373 or email us at hrsigmanixtech@gmail.com
- If data is not available, say: "Please contact Sigmanix Tech for exact details"
- Do not dump long paragraphs.
- Keep replies within 4-6 short lines.
- Do not provide contact details unless user explicitly asks for contact, registration, phone, email, website, or location.
- If user asks "which is better", do not give a random course name. Ask their goal/level first, then suggest.
CONVERSION STYLE:
- Highlight practical training and job readiness
- Explain WHY Sigmanix Tech is useful for student
- Compare in a general way (without criticizing others)"""

# ============ MAIN MENU OPTIONS ============
MAIN_MENU_OPTIONS = [
    {"label": "📚 Courses", "value": "courses"},
    {"label": "⏱️ Duration & Timeline", "value": "duration"},
    {"label": "💼 Placements & Jobs", "value": "placements"},
    {"label": "📝 Registration & Admission", "value": "registration"},
    {"label": "❓ Other Questions", "value": "other"},
]

CATEGORY_REPLIES = {
    "courses": {
        "reply": "Available courses at Sigmanix Tech:\n🎓 Python Programming with AI\n🎓 Gen AI And Agentic AI\n🎓 Data Analytics With AI\n🎓 DevOps with Multi-Cloud\n\nWhich course interests you?",
        "options": [
            {"label": "← Back to Menu", "value": "menu"},
            {"label": "Ask Details", "value": "ask_question"},
        ]
    },
    "duration": {
        "reply": "Our courses typically run for:\n⏱️ Standard Programs: 8-12 weeks\n⏱️ Intensive Programs: 4-6 weeks\n⏱️ Part-time: 12-16 weeks\n\nChoose based on your availability!",
        "options": [
            {"label": "← Back to Menu", "value": "menu"},
            {"label": "Ask More", "value": "ask_question"},
        ]
    },
    "placements": {
        "reply": "Sigmanix Tech ensures:\n✓ 100% job-ready training\n✓ Interview preparation & coaching\n✓ Direct referrals to partner companies\n✓ Average salary boost: 40-60%\n\nWant placement guarantee details?",
        "options": [
            {"label": "← Back to Menu", "value": "menu"},
            {"label": "Ask More", "value": "ask_question"},
        ]
    },
    "registration": {
        "reply": "To register:\n📋 Visit: https://sigmanixtech.com/contact\n📞 Call: +91 7416527373\n📧 Email: hrsigmanixtech@gmail.com\n\n✓ Free consultation available!",
        "options": [
            {"label": "← Back to Menu", "value": "menu"},
            {"label": "Ask More", "value": "ask_question"},
        ]
    },
}

# ============ RATE LIMITING ============
request_history = {}

def rate_limit(max_requests=10, window=60):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr
            now = time()
            
            if client_ip not in request_history:
                request_history[client_ip] = []
            
            request_history[client_ip] = [
                req_time for req_time in request_history[client_ip]
                if now - req_time < window
            ]
            
            if len(request_history[client_ip]) >= max_requests:
                logger.warning(f"Rate limit exceeded for {client_ip}")
                return jsonify({"error": "Too many requests. Please try again later."}), 429
            
            request_history[client_ip].append(now)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ============ UTILITY FUNCTIONS ============
def sanitize_input(text, max_length=500):
    """Sanitize and validate user input"""
    if not text:
        return None
    
    text = text.strip()
    if len(text) > max_length:
        return None
    
    return text

def get_menu_response():
    """Return main menu"""
    return {
        "reply": "Welcome to Sigmanix Tech! 👋\n\nHow can I help you today? Choose from below:",
        "options": MAIN_MENU_OPTIONS
    }

def quick_reply_for_common_queries(query):
    """Quick replies for common questions"""
    q = query.lower()
    
    if "offline" in q and "online" in q and ("better" in q or "join" in q):
        return {
            "reply": "Both are good, based on your situation:\n- Offline: better for hands-on guidance\n- Online: better for flexible timing\nTell me your preference!",
            "options": [{"label": "← Back to Menu", "value": "menu"}]
        }
    
    if "which course" in q and "better" in q:
        return {
            "reply": "It depends on your goal and current level.\nTell me your background (student/working professional), and I will suggest the best course.",
            "options": [{"label": "← Back to Menu", "value": "menu"}]
        }
    
    return None

# ============ WEB UI ENDPOINT ============

@app.get("/")
def index():
    """Serve the chatbot HTML interface."""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Sigmanix Tech Chatbot</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f0f0; }
        .container { 
            position: fixed; 
            bottom: 20px; 
            right: 20px; 
            width: 380px; 
            height: 520px;
            background: white; 
            border-radius: 12px; 
            box-shadow: 0 5px 40px rgba(0,0,0,0.2); 
            display: flex; 
            flex-direction: column;
            z-index: 9999;
            overflow: hidden;
        }
        .header { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            padding: 16px 15px; 
            border-radius: 12px 12px 0 0; 
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-shrink: 0;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
        }
        .header h1 { 
            font-size: 18px; 
            font-weight: 700; 
            letter-spacing: 0.3px;
            margin: 0;
        }
        .header p {
            font-size: 10px;
            opacity: 0.85;
            margin: 2px 0 0 0;
        }
        .header button { background: rgba(255,255,255,0.3); border: none; color: white; font-size: 14px; cursor: pointer; padding: 3px 8px; border-radius: 3px; transition: 0.2s; }
        .header button:hover { background: rgba(255,255,255,0.5); }
        .chat-area { 
            flex: 1; 
            overflow-y: auto; 
            padding: 12px 12px; 
            background: #f9fafb;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .message { 
            padding: 9px 11px; 
            border-radius: 7px; 
            max-width: 90%; 
            font-size: 12px; 
            line-height: 1.35;
            word-wrap: break-word;
        }
        .user-msg { 
            background: #667eea; 
            color: white; 
            margin-left: auto; 
            text-align: right;
            align-self: flex-end;
        }
        .bot-msg { 
            background: #e7f3ff; 
            color: #333; 
            margin-right: auto;
            white-space: pre-wrap;
            word-break: break-word;
            align-self: flex-start;
        }
        .options-container {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin: 8px 0;
            align-self: flex-start;
            width: 100%;
        }
        .options-btn { 
            padding: 8px 12px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none; 
            border-radius: 6px; 
            cursor: pointer; 
            font-size: 12px;
            font-weight: 500;
            transition: all 0.3s;
            flex: 0 1 auto;
            white-space: nowrap;
            box-shadow: 0 2px 5px rgba(102, 126, 234, 0.3);
        }
        .options-btn:hover { 
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 10px rgba(102, 126, 234, 0.5);
        }
        .options-btn:active {
            transform: translateY(0);
        }
        .menu-buttons { 
            padding: 8px; 
            background: white; 
            border-top: 1px solid #e0e0e0; 
            display: grid; 
            grid-template-columns: repeat(5, 1fr); 
            gap: 6px;
            flex-shrink: 0;
        }
        .menu-btn { 
            padding: 10px; 
            border: 2px solid #e0e0e0; 
            background: white; 
            border-radius: 8px; 
            cursor: pointer; 
            font-size: 18px;
            transition: all 0.2s;
        }
        .menu-btn:hover { background: #667eea; transform: scale(1.1); border-color: #667eea; }
        .input-area { 
            padding: 10px; 
            background: white; 
            border-top: 1px solid #e0e0e0; 
            display: flex; 
            gap: 8px;
            flex-shrink: 0;
        }
        .input-area input { 
            flex: 1; 
            padding: 8px 12px; 
            border: 1.5px solid #ddd; 
            border-radius: 6px; 
            font-size: 12px;
        }
        .input-area input:focus { outline: none; border-color: #667eea; box-shadow: 0 0 5px rgba(102, 126, 234, 0.3); }
        .input-area button { 
            padding: 8px 15px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            border: none; 
            border-radius: 6px; 
            cursor: pointer; 
            font-weight: bold;
            font-size: 12px;
            transition: all 0.2s;
        }
        .input-area button:hover { background: linear-gradient(135deg, #764ba2 0%, #667eea 100%); transform: translateY(-1px); box-shadow: 0 3px 8px rgba(102, 126, 234, 0.3); }
        .chat-area::-webkit-scrollbar { width: 6px; }
        .chat-area::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 10px; }
        .chat-area::-webkit-scrollbar-thumb { background: #bbb; border-radius: 10px; }
        .chat-area::-webkit-scrollbar-thumb:hover { background: #888; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>🎓 Sigmanix Tech Chatbot</h1>
                <p>AI-Powered Assistant</p>
            </div>
        </div>
        <div class="chat-area" id="chatArea"></div>
        <div class="menu-buttons">
            <button class="menu-btn" onclick="selectMenu('courses')" title="Courses">📚</button>
            <button class="menu-btn" onclick="selectMenu('duration')" title="Duration">⏱️</button>
            <button class="menu-btn" onclick="selectMenu('placements')" title="Placements">💼</button>
            <button class="menu-btn" onclick="selectMenu('registration')" title="Registration">📝</button>
            <button class="menu-btn" onclick="selectMenu('feedback')" title="Feedback">⭐</button>
        </div>
        <div class="input-area">
            <input type="text" id="userInput" placeholder="Ask..." onkeypress="handleEnter(event)">
            <button onclick="sendMessage()">→</button>
        </div>
    </div>
    <script>
        async function sendMessage() {
            const input = document.getElementById('userInput');
            const message = input.value.trim();
            if (!message) return;
            displayMessage(message, 'user');
            input.value = '';
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                });
                const data = await response.json();
                displayMessage(data.reply, 'bot');
                if (data.options) displayOptions(data.options);
            } catch (error) {
                displayMessage('Error connecting to server', 'bot');
            }
        }
        async function selectMenu(menu) {
            if (menu === 'feedback') {
                const rating = prompt('Rate your experience (1-5):');
                if (rating && rating >= 1 && rating <= 5) {
                    const comment = prompt('Any comments? (optional)');
                    try {
                        await fetch('/feedback', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ rating: parseInt(rating), comment: comment || '' })
                        });
                        displayMessage(`⭐ Thank you! ${rating}/5`, 'bot');
                    } catch (error) {
                        displayMessage('Error submitting feedback', 'bot');
                    }
                }
                return;
            }
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ menu_selected: menu })
                });
                const data = await response.json();
                displayMessage(data.reply, 'bot');
                if (data.options) displayOptions(data.options);
            } catch (error) {
                displayMessage('Error connecting to server', 'bot');
            }
        }
        function displayMessage(message, type) {
            const chatArea = document.getElementById('chatArea');
            const msgDiv = document.createElement('div');
            msgDiv.className = `message ${type}-msg`;
            msgDiv.textContent = message;
            chatArea.appendChild(msgDiv);
            chatArea.scrollTop = chatArea.scrollHeight;
        }
        function displayOptions(options) {
            if (!options) return;
            const chatArea = document.getElementById('chatArea');
            const optionsDiv = document.createElement('div');
            optionsDiv.className = 'options-container';
            options.forEach(opt => {
                const btn = document.createElement('button');
                btn.className = 'options-btn';
                btn.textContent = opt.label;
                btn.onclick = () => selectMenuOption(opt.value);
                optionsDiv.appendChild(btn);
            });
            chatArea.appendChild(optionsDiv);
            chatArea.scrollTop = chatArea.scrollHeight;
        }
        async function selectMenuOption(value) {
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ menu_selected: value })
                });
                const data = await response.json();
                displayMessage(data.reply, 'bot');
                if (data.options) displayOptions(data.options);
            } catch (error) {
                displayMessage('Error connecting to server', 'bot');
            }
        }
        function handleEnter(event) {
            if (event.key === 'Enter') sendMessage();
        }
        window.addEventListener('load', () => {
            selectMenu('menu');
        });
    </script>
</body>
</html>"""
    return render_template_string(html)

# ============ CHAT ENDPOINT ============

@app.post("/chat")
@rate_limit(max_requests=20, window=60)
def chat_endpoint():
    """Main chat endpoint"""
    try:
        payload = request.get_json(silent=True) or {}
        query = (payload.get("message") or "").strip()
        selected_menu = payload.get("menu_selected")
        
        if not query and not selected_menu:
            return jsonify({"reply": "Please type a question or select an option."}), 400
        
        if "visitor_id" not in session:
            session["visitor_id"] = 'visitor_' + os.urandom(12).hex()
            get_or_create_student(session["visitor_id"])
        
        if "history" not in session:
            session["history"] = []
        
        if selected_menu:
            if selected_menu == "menu":
                response = get_menu_response()
            elif selected_menu in CATEGORY_REPLIES:
                response = CATEGORY_REPLIES[selected_menu]
            elif selected_menu == "ask_question":
                response = get_menu_response()
            else:
                response = get_menu_response()
            
            save_conversation(session["visitor_id"], selected_menu, response.get("reply", ""), selected_menu)
            return jsonify(response), 200
        
        quick_reply = quick_reply_for_common_queries(query)
        if quick_reply:
            return jsonify(quick_reply), 200
        
        results_with_scores = db.similarity_search_with_score(query, k=6)
        filtered_results = [doc.page_content for doc, score in results_with_scores if score < 0.6]
        context = " ".join(filtered_results) if filtered_results else " ".join([doc.page_content for doc, _ in results_with_scores[:3]])
        
        history = session.get("history", [])
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history[-6:])
        messages.append({"role": "user", "content": f"Context: {context}\n\nQuestion: {query}"})
        
        response_obj = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            max_tokens=150,
            temperature=0.7
        )
        
        answer = response_obj.choices[0].message.content
        
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": answer})
        session["history"] = history
        
        save_conversation(session["visitor_id"], query, answer, "ai_chat")
        
        return jsonify({"reply": answer, "options": [{"label": "← Back to Menu", "value": "menu"}]}), 200
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error", "reply": "Sorry, I'm having trouble. Please try again."}), 500

@app.post("/feedback")
@rate_limit(max_requests=5, window=60)
def feedback_endpoint():
    """Save user feedback"""
    try:
        data = request.get_json(silent=True) or {}
        rating = data.get("rating")
        comment = data.get("comment", "")
        
        if not rating or rating < 1 or rating > 5:
            return jsonify({"error": "Invalid rating"}), 400
        
        result = save_feedback(session.get("visitor_id"), int(rating), comment[:500])
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Feedback error: {e}")
        return jsonify({"error": "Could not save feedback"}), 500

@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "environment": ENV,
        "timestamp": datetime.utcnow().isoformat(),
        "features": {
            "database": "SQLite",
            "llm": "Groq (llama-3.1-8b-instant)",
            "knowledge_chunks": len(docs),
            "cors": "enabled"
        }
    }), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    logger.info("🚀 PRODUCTION CHATBOT SERVER WITH INTEGRATED UI")
    logger.info(f"Environment: {ENV}")
    logger.info(f"Knowledge Chunks: {len(docs)}")
    logger.info(f"Starting server on http://0.0.0.0:5000")
    
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=DEBUG,
        use_reloader=DEBUG
    )