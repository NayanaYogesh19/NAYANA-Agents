# QUICK SETUP GUIDE

## ⚡ 5-Minute Setup

### Step 1: Install Python
- Download Python 3.8+ from https://www.python.org/downloads/
- During installation, check "Add Python to PATH"

### Step 2: Setup Project
```bash
cd C:\faq-optimizer-agent
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Step 3: Get API Keys

#### OpenRouter (Required)
1. Go to https://openrouter.ai/
2. Sign up or log in
3. Go to Keys section
4. Create a new API key
5. Copy the key (starts with "sk-or-...")

#### LangSmith (Required)
1. Go to https://smith.langchain.com/
2. Sign up or log in
3. Go to Settings → API Keys
4. Create a new API key
5. Copy the key

#### Supabase (Required)
1. Go to https://supabase.com/
2. Create a new project
3. Go to Project Settings → API
4. Copy:
   - Project URL (SUPABASE_URL)
   - anon/public key (SUPABASE_KEY)
5. Go to SQL Editor and run:
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

### Step 4: Configure Environment
```bash
copy .env.example .env  # Windows
cp .env.example .env    # Mac/Linux
```

Edit `.env` file and paste your API keys:
```
OPENROUTER_API_KEY=sk-or-v1-YOUR-KEY-HERE
LANGSMITH_API_KEY=lsv2-YOUR-KEY-HERE
SUPABASE_URL=https://YOUR-PROJECT.supabase.co
SUPABASE_KEY=YOUR-ANON-KEY-HERE
```

### Step 5: Run the Agent
```bash
# Windows
start.bat

# Mac/Linux
chmod +x start.sh
./start.sh
```

### Step 6: Use the Application
1. Open browser: http://localhost:8000
2. Enter website URL and topic
3. Review generated questions
4. Select questions to answer
5. View and export your optimized FAQs!

## 🎯 Testing the Agent

Try these example inputs:
- **URL**: https://www.anthropic.com
- **Topic**: AI Safety and Claude

## ❓ Common Issues

### "Module not found" error
```bash
pip install -r requirements.txt --upgrade
```

### "Port 8000 already in use"
Edit `.env` and change `APP_PORT=8001`

### "Invalid API key"
- Double-check keys in `.env`
- Ensure no extra spaces before/after keys
- Verify keys are active in respective dashboards

### Web scraping fails
- Check if website blocks bots
- Try a different URL
- Ensure URL includes http:// or https://

## 📞 Need Help?

Check logs in `logs/app.log` for detailed error messages.

---

That's it! You're ready to generate optimized FAQs! 🚀
