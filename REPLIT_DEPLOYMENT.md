# Replit Deployment Guide - Complete

## Why Replit?
✅ **Completely FREE** - No credit card needed
✅ **Always Running** - 24/7 uptime (24/7 on free tier)
✅ **Easy Setup** - Auto-installs dependencies
✅ **Public URL** - Instant shareable link
✅ **Built-in Database** - SQLite ready
✅ **No Configuration** - Works out of the box

---

## Step-by-Step Setup

### 1. Create Replit Account (1 min)
- Go to https://replit.com
- Sign up with GitHub or email
- Free account created

### 2. Import This Repository (2 min)

**Option A: Direct GitHub Import**
1. Click **+ Create** button
2. Select **Import from GitHub**
3. Paste: `https://github.com/vivvek69/sigmanix-chatbot`
4. Click **Import**
5. Wait 1-2 minutes for files to download

**Option B: Manual Upload**
1. Click **+ Create** → Select **Python**
2. Name the project: `sigmanix-chatbot`
3. Click **Upload Files**
4. Select and upload all project files

### 3. Add Groq API Key to Secrets (1 min)

1. Click **Secrets** button (lock icon on left sidebar)
2. Click **New Secret**
3. Enter:
   - **Key**: `GROQ_API_KEY`
   - **Value**: Your Groq API key (get from https://console.groq.com/)
4. Click **Add Secret**
5. Close secrets panel

### 4. Run the Application (1 min)

1. Click the big **RUN** button (or press Ctrl+Enter)
2. Wait for the terminal to show:
   ```
   Listening on 0.0.0.0:5000
   ```
3. Click the **Web** tab on the right
4. Your chatbot URL appears!

### 5. Access Your Chatbot (instant)

Click the URL shown in the Web tab. Your chatbot is live!

It will look like: `https://yourname-sigmanix-chatbot.replit.dev`

---

## Verification Checklist

- [ ] Repository imported or files uploaded
- [ ] `GROQ_API_KEY` secret added
- [ ] Application running (see "Listening on 0.0.0.0:5000" in terminal)
- [ ] Web tab shows a URL
- [ ] Chatbot UI loads in browser
- [ ] Chat works with responses
- [ ] Menu buttons respond

---

## Features Working

✅ **Web UI** - Built-in chatbot interface
✅ **Menu System** - 5 category buttons
✅ **Chat** - AI responses via Groq
✅ **Database** - Auto-created, saves conversations
✅ **Analytics** - Admin endpoints track usage
✅ **Feedback** - User ratings/comments
✅ **CORS** - React integration ready

---

## Troubleshooting

### ❌ "GROQ_API_KEY not set"
- **Solution**: Add the secret in Secrets panel
- Make sure the key name is exactly `GROQ_API_KEY`
- Restart the application after adding

### ❌ "Connection refused"
- **Solution**: Wait 30 seconds for server to fully start
- Click RUN again if it stops
- Check terminal for errors

### ❌ "data.txt not found"
- **Solution**: Make sure `data.txt` file was uploaded
- Re-upload if missing
- Check file list in left sidebar

### ❌ Chatbot responds but no menu buttons
- **Solution**: This is normal sometimes on first load
- Refresh the page
- Try sending a message

---

## Sharing Your Chatbot

### Public URL
- Everyone can access via: `https://yourname-sigmanix-chatbot.replit.dev`
- No login required
- Works on mobile too!

### Integration
- Use `/chat` endpoint for custom integrations
- Use `/feedback` for ratings
- Use `/health` to check status

---

## Advanced: Keep Server Running

Replit free tier may pause after 1 hour of inactivity.

**To keep it always running:**
1. Click **Multiplayer** (top right)
2. Enable **Always on** (if available on your plan)
3. Your chatbot stays up 24/7

**Alternative:** Use Replit's paid plan ($7/month) for guaranteed uptime.

---

## Admin Panel

**Access analytics at:**
- `https://yourname-sigmanix-chatbot.replit.dev/admin/students`
- `https://yourname-sigmanix-chatbot.replit.dev/admin/analytics`

**View:**
- Total visitors
- Interest levels
- Conversation history
- Feedback ratings
- Popular categories

---

## Next Steps

1. **Customize Data**: Edit `data.txt` with your content
2. **Modify Prompts**: Edit SYSTEM_PROMPT in `chatbot_production.py`
3. **Add Features**: Extend with admin_routes.py
4. **Deploy**: Your public URL is production-ready!

---

## Support

**Issues?**
1. Check the terminal output for errors
2. Restart with RUN button
3. Verify all files are present
4. Check GROQ_API_KEY is valid

**Files Required:**
- `chatbot_production.py` - Main app
- `database.py` - Database layer
- `admin_routes.py` - Admin features
- `data.txt` - Knowledge base
- `requirements.txt` - Dependencies
- `.env.example` - Configuration template
- `.replit` - Replit configuration

---

**Status: ✅ PRODUCTION READY**

Your Sigmanix Tech chatbot is ready to serve students!
