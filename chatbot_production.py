from flask import Flask, render_template_string, request, session, jsonify
from flask_cors import CORS
import os
import logging
import json
from datetime import datetime, timedelta
from database import (
    init_database,
    get_or_create_student,
    save_conversation,
    save_feedback,
    get_student_analytics,
)
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains.question_answering import load_qa_chain
from langchain_groq import ChatGroq
import re
from functools import wraps
from collections import defaultdict
import time

# ============ SETUP ============
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "sigmanix-secret-dev")
CORS(app, origins=["http://localhost:3000"])

# Logging setup with UTF-8
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Database initialization
init_database()
logger.info("✅ Database initialized successfully")

# Groq API setup
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    logger.error("❌ GROQ_API_KEY not found in environment variables")
else:
    groq_llm = ChatGroq(
        temperature=0.7,
        groq_api_key=groq_api_key,
        model_name="llama-3.1-8b-instant",
    )
    logger.info("✅ Groq client initialized")

# Knowledge base setup
logger.info("📚 Loading knowledge base...")
with open("data.txt", "r", encoding="utf-8") as file:
    raw_text = file.read()

text_splitter = CharacterTextSplitter(
    separator="\n",
    chunk_size=500,
    chunk_overlap=50,
    length_function=len,
)
text_chunks = text_splitter.split_text(raw_text)
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
knowledge_base = FAISS.from_texts(text_chunks, embeddings)
logger.info(f"✅ Created {len(text_chunks)} chunks from knowledge base")

# System prompt
SYSTEM_PROMPT = """You are a helpful AI assistant for Sigmanix Tech, an educational institute offering courses in Python, AI, Data Analytics, and DevOps. 
Provide accurate, concise information about courses, placements, admissions, and career guidance.
If asked something unrelated to Sigmanix Tech, politely redirect to the main topics.
Always be professional and supportive."""

# Menu responses
MENU_RESPONSES = {
    "courses": {
        "reply": "📚 **Available Courses:**\n🎓 Python Programming with AI\n🎓 Gen AI And Agentic AI\n🎓 Data Analytics With AI\n🎓 DevOps with Multi-Cloud\n\nWhich course interests you?",
        "options": [
            {"label": "← Back to Menu", "value": "menu"},
            {"label": "Ask Details", "value": "course_details"},
        ],
    },
    "duration": {
        "reply": "⏱️ **Course Durations:**\n• Python Programming: 2 months (40 hours)\n• Gen AI: 3 months (60 hours)\n• Data Analytics: 2.5 months (50 hours)\n• DevOps: 3 months (60 hours)\n\nWould you like more details?",
        "options": [
            {"label": "← Back to Menu", "value": "menu"},
            {"label": "Learn More", "value": "learn_more"},
        ],
    },
    "placements": {
        "reply": "💼 **Placement Guarantee:**\n✓ 100% job-ready training\n✓ Interview preparation & coaching\n✓ Direct referrals to partner companies\n✓ Average salary boost: 40-60%\n\nWant placement guarantee details?",
        "options": [
            {"label": "← Back to Menu", "value": "menu"},
            {"label": "Ask More", "value": "ask_more"},
        ],
    },
    "registration": {
        "reply": "📝 **Registration Process:**\n1️⃣ Fill the application form on our website\n2️⃣ Complete payment\n3️⃣ Receive course access within 24 hours\n4️⃣ Start learning immediately\n\nReady to register?",
        "options": [
            {"label": "← Back to Menu", "value": "menu"},
            {"label": "Register Now", "value": "register"},
        ],
    },
    "menu": {
        "reply": "Welcome to Sigmanix Tech! 👋\n\nHow can I help you today? Choose from below:",
        "options": [
            {"label": "📚 Courses", "value": "courses"},
            {"label": "⏱️ Duration & Timeline", "value": "duration"},
            {"label": "💼 Placements & Jobs", "value": "placements"},
            {"label": "📝 Registration & Admission", "value": "registration"},
            {"label": "❓ Other Questions", "value": "other"},
        ],
    },
}

# Rate limiting
request_log = defaultdict(list)

def rate_limit(max_requests=20, window=60):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            client_id = request.remote_addr
            now = time.time()
            request_log[client_id] = [t for t in request_log[client_id] if now - t < window]
            if len(request_log[client_id]) >= max_requests:
                return jsonify({"error": "Rate limit exceeded. Try again later."}), 429
            request_log[client_id].append(now)
            return f(*args, **kwargs)
        return wrapper
    return decorator

def sanitize_response(text):
    return re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', text)

def get_menu_response(menu_selected):
    return MENU_RESPONSES.get(menu_selected, None)

def quick_reply(query):
    query_lower = query.lower()
    if "course" in query_lower:
        return get_menu_response("courses")
    elif "duration" in query_lower or "time" in query_lower:
        return get_menu_response("duration")
    elif "placement" in query_lower or "job" in query_lower:
        return get_menu_response("placements")
    elif "register" in query_lower or "admission" in query_lower:
        return get_menu_response("registration")
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
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
        .container { width: 100%; max-width: 450px; height: 680px; background: white; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); display: flex; flex-direction: column; overflow: hidden; animation: slideIn 0.3s ease-out; }
        @keyframes slideIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 24px 20px; flex-shrink: 0; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.25); }
        .header h1 { font-size: 22px; font-weight: 700; letter-spacing: 0.5px; margin: 0 0 4px 0; line-height: 1.3; }
        .header p { font-size: 13px; opacity: 0.9; margin: 0; font-weight: 500; }
        .chat-area { flex: 1; overflow-y: auto; padding: 16px; background: #f8f9fc; display: flex; flex-direction: column; gap: 12px; }
        .message-wrapper { display: flex; gap: 8px; margin-bottom: 4px; animation: fadeIn 0.25s ease-out; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .bot-wrapper { justify-content: flex-start; }
        .user-wrapper { justify-content: flex-end; }
        .message { padding: 12px 14px; border-radius: 12px; max-width: 85%; font-size: 13px; line-height: 1.5; word-wrap: break-word; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
        .user-msg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 14px 14px 4px 14px; font-weight: 500; }
        .bot-msg { background: #ffffff; color: #2c3e50; border-radius: 14px 14px 14px 4px; white-space: pre-wrap; word-break: break-word; border: 1px solid #e0e7ff; }
        .options-container { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 4px 0; width: 100%; animation: fadeIn 0.25s ease-out; }
        .options-btn { padding: 10px 14px; background: white; color: #667eea; border: 2px solid #667eea; border-radius: 8px; cursor: pointer; font-size: 12px; font-weight: 600; transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1); flex: 0 1 auto; white-space: nowrap; }
        .options-btn:hover { background: #667eea; color: white; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3); }
        .menu-buttons { padding: 12px; background: white; border-top: 1px solid #e0e7ff; display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; flex-shrink: 0; }
        .menu-btn { padding: 12px; border: 2px solid #e0e7ff; background: white; border-radius: 10px; cursor: pointer; font-size: 22px; transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); display: flex; align-items: center; justify-content: center; }
        .menu-btn:hover { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-color: #667eea; transform: scale(1.15); box-shadow: 0 4px 12px rgba(102, 126, 234, 0.25); }
        .menu-btn:active { transform: scale(1.05); }
        .input-area { padding: 14px; background: white; border-top: 1px solid #e0e7ff; display: flex; gap: 10px; flex-shrink: 0; }
        .input-area input { flex: 1; padding: 11px 14px; border: 2px solid #e0e7ff; border-radius: 8px; font-size: 13px; font-family: inherit; transition: all 0.25s; }
        .input-area input:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); }
        .input-area input::placeholder { color: #999; }
        .input-area button { padding: 11px 18px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 700; font-size: 16px; transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1); display: flex; align-items: center; justify-content: center; min-width: 44px; height: 44px; }
        .input-area button:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(102, 126, 234, 0.3); }
        .input-area button:active { transform: translateY(0); }
        .chat-area::-webkit-scrollbar { width: 6px; }
        .chat-area::-webkit-scrollbar-track { background: transparent; }
        .chat-area::-webkit-scrollbar-thumb { background: #ddd; border-radius: 3px; }
        .chat-area::-webkit-scrollbar-thumb:hover { background: #999; }
        @media (max-width: 480px) { .container { height: calc(100vh - 40px); max-width: 100%; } .header { padding: 16px; } .header h1 { font-size: 18px; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎓 Sigmanix Tech Chatbot</h1>
            <p>AI-Powered Career Assistant</p>
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
            <input type="text" id="userInput" placeholder="Ask a question..." onkeypress="handleEnter(event)">
            <button onclick="sendMessage()" title="Send">↑</button>
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
                const response = await fetch('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: message }) });
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
                        await fetch('/feedback', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ rating: parseInt(rating), comment: comment || '' }) });
                        displayMessage(`⭐ Thank you! ${rating}/5`, 'bot');
                    } catch (error) { displayMessage('Error submitting feedback', 'bot'); }
                }
                return;
            }
            try {
                const response = await fetch('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ menu_selected: menu }) });
                const data = await response.json();
                displayMessage(data.reply, 'bot');
                if (data.options) displayOptions(data.options);
            } catch (error) { displayMessage('Error connecting to server', 'bot'); }
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
                const response = await fetch('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ menu_selected: value }) });
                const data = await response.json();
                displayMessage(data.reply, 'bot');
                if (data.options) displayOptions(data.options);
            } catch (error) { displayMessage('Error connecting to server', 'bot'); }
        }
        function handleEnter(event) { if (event.key === 'Enter') sendMessage(); }
        window.addEventListener('load', () => { selectMenu('menu'); });
    </script>
</body>
</html>"""
    return render_template_string(html)

# ============ CHAT ENDPOINT (for UI & React) ============

@app.post("/chat")
@rate_limit(max_requests=20, window=60)
def chat_endpoint():
    """Main chat endpoint - works with UI and React."""
    try:
        payload = request.get_json(silent=True) or {}
        query = (payload.get("message") or "").strip()
        selected_menu = payload.get("menu_selected")
        
        if not query and not selected_menu:
            return jsonify({"reply": "Please type a question or select an option."}), 400
        
        # Initialize session
        if "visitor_id" not in session:
            session["visitor_id"] = 'visitor_' + os.urandom(12).hex()
            get_or_create_student(session["visitor_id"])
            logger.info(f"New visitor: {session['visitor_id']}")
        
        # Handle menu selection
        if selected_menu:
            menu_response = get_menu_response(selected_menu)
            if menu_response:
                save_conversation(
                    session["visitor_id"],
                    f"Menu: {selected_menu}",
                    menu_response["reply"],
                )
                return jsonify({
                    "reply": menu_response["reply"],
                    "options": menu_response.get("options", []),
                })
        
        # Try quick reply first
        quick = quick_reply(query)
        if quick:
            save_conversation(session["visitor_id"], query, quick["reply"])
            return jsonify({
                "reply": quick["reply"],
                "options": quick.get("options", []),
            })
        
        # Use LLM for knowledge base search
        query_result = knowledge_base.similarity_search(query, k=3)
        if not query_result:
            reply = "I don't have information about that. Please ask about our courses, duration, placements, or registration."
        else:
            chain = load_qa_chain(groq_llm, chain_type="stuff")
            response = chain.run(input_documents=query_result, question=query)
            reply = sanitize_response(response.strip())
        
        save_conversation(session["visitor_id"], query, reply)
        return jsonify({"reply": reply, "options": []})
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({"reply": "Error processing your request. Please try again."}), 500

@app.post("/feedback")
def feedback_endpoint():
    """Save user feedback."""
    try:
        if "visitor_id" not in session:
            return jsonify({"error": "Session not found"}), 400
        
        data = request.get_json(silent=True) or {}
        rating = data.get("rating", 0)
        comment = data.get("comment", "")
        
        if not (1 <= rating <= 5):
            return jsonify({"error": "Rating must be 1-5"}), 400
        
        save_feedback(session["visitor_id"], rating, comment)
        return jsonify({"success": True, "message": "Feedback saved"})
    except Exception as e:
        logger.error(f"Feedback error: {str(e)}")
        return jsonify({"error": "Error saving feedback"}), 500

@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime": "running",
    })

# ============ ADMIN ANALYTICS ============

@app.get("/admin/students")
def get_students():
    """Get all students data."""
    try:
        analytics = get_student_analytics()
        return jsonify({"students": analytics})
    except Exception as e:
        logger.error(f"Analytics error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.get("/admin/analytics")
def get_analytics():
    """Get system analytics."""
    try:
        analytics = get_student_analytics()
        return jsonify({
            "total_students": len(analytics),
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        logger.error(f"Analytics error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ============ ERROR HANDLERS ============

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

# ============ MAIN ============

if __name__ == "__main__":
    logger.info("✅ Starting Sigmanix Chatbot...")
    logger.info("🌐 Server running on http://localhost:5000")
    logger.info("📚 Knowledge base ready with %d chunks", len(text_chunks))
    app.run(host="0.0.0.0", port=5000, debug=False)
