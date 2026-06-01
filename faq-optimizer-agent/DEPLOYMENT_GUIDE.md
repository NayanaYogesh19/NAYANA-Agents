# 🚀 FAQ OPTIMIZER AGENT - DEPLOYMENT INSTRUCTIONS

## ✅ What You Have

A **production-ready** FAQ Optimizer Agent with:
- ✅ Complete backend (FastAPI)
- ✅ Modern frontend (HTML/CSS/JS)
- ✅ LangChain integration
- ✅ OpenRouter (GPT-4o-mini)
- ✅ LangSmith tracing
- ✅ Supabase database
- ✅ PDF export functionality
- ✅ Error handling & logging
- ✅ All validations in place

## 📦 Extract the Project

1. Download the `faq-optimizer-agent` folder
2. Place it in `C:\` drive (or any location)
   ```
   C:\faq-optimizer-agent\
   ```

## 🎯 ONE-TIME SETUP (10 minutes)

### 1. Install Python (if not installed)
- Download from: https://www.python.org/downloads/
- Install Python 3.8 or higher
- ✅ **IMPORTANT**: Check "Add Python to PATH" during installation

### 2. Open Command Prompt
```bash
cd C:\faq-optimizer-agent
```

### 3. Create Virtual Environment
```bash
python -m venv venv
```

### 4. Activate Virtual Environment
```bash
venv\Scripts\activate
```
You should see `(venv)` appear in your command prompt.

### 5. Install Dependencies
```bash
pip install -r requirements.txt
```
This will install all required packages (takes 2-3 minutes).

### 6. Get Your API Keys

#### A. OpenRouter API Key
1. Go to: https://openrouter.ai/
2. Sign up / Log in
3. Click "Keys" in the sidebar
4. Click "Create Key"
5. Copy the key (starts with `sk-or-v1-...`)

#### B. LangSmith API Key
1. Go to: https://smith.langchain.com/
2. Sign up / Log in
3. Click Settings → API Keys
4. Click "Create API Key"
5. Copy the key (starts with `lsv2_...`)

#### C. Supabase Setup
1. Go to: https://supabase.com/
2. Create new project
3. Go to: Project Settings → API
4. Copy:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon/public key**: Long string starting with `eyJ...`

5. Go to SQL Editor and run this:
```sql
CREATE TABLE faqs (
    id BIGSERIAL PRIMARY KEY,
    company_name TEXT NOT NULL,
    website_url TEXT NOT NULL,
    topic TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('AEO', 'GEO', 'SEO')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_faqs_category ON faqs(category);
CREATE INDEX idx_faqs_created_at ON faqs(created_at);
CREATE INDEX idx_faqs_company ON faqs(company_name);
```

### 7. Configure Environment Variables

1. Copy the example file:
```bash
copy .env.example .env
```

2. Open `.env` file in Notepad or VS Code

3. Replace the placeholder values with your actual API keys:

```env
OPENROUTER_API_KEY=sk-or-v1-YOUR-ACTUAL-KEY-HERE
LANGSMITH_API_KEY=lsv2_YOUR-ACTUAL-KEY-HERE
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-actual-supabase-anon-key-here
```

4. Save and close the file

## 🎬 RUNNING THE AGENT

### Method 1: Using Startup Script (Easiest)
```bash
start.bat
```

### Method 2: Manual Start
```bash
# Activate virtual environment (if not already activated)
venv\Scripts\activate

# Start the server
python backend/main.py
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Open the Application
Open your browser and go to:
```
http://localhost:8000
```

## 🎯 HOW TO USE

### Step 1: Generate Questions
1. Enter website URL (e.g., `https://www.anthropic.com`)
2. Enter topic (e.g., `AI Safety`)
3. Click "Generate Questions"
4. Wait 10-30 seconds

### Step 2: Review & Select
1. Review the 15 generated questions
2. Questions are grouped by:
   - **AEO**: For AI assistants
   - **GEO**: For Google featured snippets
   - **SEO**: For search engines
3. Uncheck any questions you don't want
4. Click "Generate Answers for Selected Questions"

### Step 3: View & Export
1. View your optimized FAQs
2. Click "Export to PDF" to download
3. FAQs are automatically saved to Supabase

## 🔍 TESTING THE AGENT

Try these examples:

**Example 1:**
- URL: `https://www.anthropic.com`
- Topic: `Claude AI Assistant`

**Example 2:**
- URL: `https://www.openai.com`
- Topic: `ChatGPT Features`

**Example 3:**
- URL: `https://stripe.com`
- Topic: `Payment Processing`

## 🐛 TROUBLESHOOTING

### "pip is not recognized"
→ Python not added to PATH. Reinstall Python with "Add to PATH" checked.

### "No module named 'fastapi'"
→ Virtual environment not activated. Run: `venv\Scripts\activate`

### "Port 8000 already in use"
→ Edit `.env` and change: `APP_PORT=8001`

### "Failed to scrape website"
→ Try a different URL. Some websites block scrapers.

### "Invalid API key"
→ Check your `.env` file. Ensure no extra spaces around keys.

### Application not loading
→ Check `logs/app.log` for error details.

## 📊 MONITORING

### View LangSmith Dashboard
1. Go to: https://smith.langchain.com/
2. Select project: `faq-optimizer-agent`
3. See all LLM calls, token usage, and latency

### View Supabase Data
1. Go to your Supabase project
2. Click "Table Editor"
3. Select "faqs" table
4. View all generated FAQs

## 🎉 SUCCESS CHECKLIST

- ✅ Python installed
- ✅ Virtual environment created
- ✅ Dependencies installed
- ✅ API keys configured in .env
- ✅ Supabase table created
- ✅ Server starts without errors
- ✅ Can access http://localhost:8000
- ✅ Can generate questions
- ✅ Can generate answers
- ✅ FAQs stored in database
- ✅ PDF export works

## 🔒 SECURITY NOTES

- ✅ Never share your `.env` file
- ✅ Never commit `.env` to GitHub
- ✅ Keep API keys secure
- ✅ `.gitignore` is already configured

## 📝 IMPORTANT FILES

- **backend/main.py** - Main application entry point
- **backend/config.py** - Configuration & API keys loading
- **backend/services/llm_service.py** - LLM prompts and logic
- **frontend/index.html** - User interface
- **.env** - Your API keys (DO NOT SHARE)
- **logs/app.log** - Error logs and debugging info

## 🎨 CUSTOMIZATION

### Change Prompts
Edit: `backend/services/llm_service.py`
- Line 30: Question generation prompt
- Line 95-115: Answer generation prompts

### Change UI Colors
Edit: `frontend/styles.css`
- Line 8: Background gradient
- Line 139: Button colors

### Change Number of Questions
Edit: `backend/services/llm_service.py`
- Line 36: Change "EXACTLY 15" to your desired number

## 🚀 NEXT STEPS

1. ✅ Complete setup
2. ✅ Test with sample URLs
3. ✅ Generate FAQs for your website
4. ✅ Export and publish FAQs
5. ✅ Monitor in LangSmith
6. ✅ View data in Supabase

## 📞 SUPPORT

If you encounter issues:
1. Check `logs/app.log` for errors
2. Verify all API keys are correct
3. Ensure Supabase table exists
4. Try with a different website URL

---

## ✨ YOU'RE ALL SET!

Your FAQ Optimizer Agent is ready to use. Just:
1. Run `start.bat`
2. Open http://localhost:8000
3. Start generating optimized FAQs!

**Happy FAQ generating! 🎉**
