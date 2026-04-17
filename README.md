# Sigmanix Tech Chatbot

Production-ready AI chatbot using Flask, Groq LLM, and FAISS.

## Quick Deploy to Replit (FREE)

1. **Create Replit Account**: https://replit.com
2. **Import Repository**:
   - Click `+ Create`
   - Select `Import from GitHub`
   - Paste: `https://github.com/vivvek69/sigmanix-chatbot`
   - Click `Import`

3. **Add Secret**:
   - Click `Secrets` (lock icon)
   - Add: `GROQ_API_KEY` = your_key_from_https://console.groq.com
   - Save

4. **Run**:
   - Click `RUN` button
   - Click `Web` tab
   - Your URL appears!

---

## Features
- Web UI with 5 menu buttons
- React.js integration
- SQLite database
- FAISS knowledge search
- Rate limiting
- Production logging

## Tech Stack
- Flask 3.0.3
- Groq (llama-3.1-8b-instant)
- LangChain 0.2.0
- FAISS + HuggingFace Embeddings
- SQLite3

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variable
export GROQ_API_KEY="your_key"

# Run
python chatbot_production.py

# Visit: http://localhost:5000
```

## API Endpoints

- `GET /` - Web UI
- `POST /chat` - Chat API
- `POST /feedback` - Feedback API
- `GET /health` - Health check

## Deployment

### Replit (FREE)
- No credit card needed
- Always free
- Just import from GitHub

### Other Options
- Railway.app
- Render.com
- Google Cloud Run
- Fly.io

## License
MIT
