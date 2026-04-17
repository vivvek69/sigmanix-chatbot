# Contributing

Contributions welcome! Here's how:

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Submit a pull request

## Development Setup

```bash
git clone https://github.com/YOUR_USERNAME/sigmanix-chatbot.git
cd sigmanix-chatbot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Add your Groq API key
echo 'GROQ_API_KEY=your_key' > .env

# Run locally
python chatbot_production.py
```

Visit: http://localhost:5000

## Code Guidelines

- Keep it simple and readable
- Add comments for complex logic
- Follow PEP 8 style
- Test before submitting PR

---

**Happy coding!**
