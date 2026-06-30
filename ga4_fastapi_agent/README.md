# GA4 + GSC Analytics Agent

A FastAPI-powered analytics dashboard that connects to **Google Analytics 4 (GA4)** and **Google Search Console (GSC)** via OAuth2, with a polished glassmorphism frontend UI.

## Features

### GA4 Reports
- Traffic Acquisition
- User Acquisition
- Landing Pages
- Pages & Screens
- Events
- Country / City / Device / Browser / OS Reports
- Source / Medium Report
- Campaign Report
- New vs Returning Users
- Daily Trend Report

### GSC Reports
- Performance: Queries, Pages, Countries, Devices, Search Appearance, Days
- Indexing: Pages Coverage, Videos Coverage, Sitemaps
- Experience: Core Web Vitals, HTTPS Report
- Enhancements: Breadcrumb Report

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp example.env .env
```
Fill in your values in `.env`:
```
GA4_CLIENT_ID=your-google-oauth-client-id
GA4_CLIENT_SECRET=your-google-oauth-client-secret
GA4_REDIRECT_URI=http://localhost:8080/
PAGESPEED_API_KEY=your-pagespeed-api-key
```

### 3. Google Cloud Setup
- Enable **Google Analytics Data API**, **Google Analytics Admin API**, and **Google Search Console API** in your Google Cloud project
- Create OAuth 2.0 credentials (Desktop app type)
- Add your email as a test user if the app is in testing mode

### 4. Run the server
```bash
python -m uvicorn main:app --reload
```

### 5. Open the app
Visit [http://127.0.0.1:8000](http://127.0.0.1:8000)

On first run, a browser window will open for Google OAuth login. After authentication, a `token.json` is saved locally for future requests.

## Project Structure
```
ga4_fastapi_agent/
├── main.py                  # FastAPI app entry point
├── requirements.txt
├── example.env              # Template for environment variables
├── ga4/
│   ├── auth.py              # Google OAuth2 flow
│   ├── routes.py            # GA4 API endpoints
│   ├── schemas.py           # Pydantic request models
│   └── service.py           # GA4 Data API logic
├── gsc/
│   ├── routes.py            # GSC API endpoints
│   ├── schemas.py           # Pydantic request models
│   └── service.py           # Search Console API logic
└── frontend/
    ├── index.html           # Main UI
    ├── scripts.js           # Report logic & API calls
    └── style.css            # Glassmorphism UI styles
```

## Notes
- `.env` and `token.json` are excluded from version control
- The `token.json` is auto-generated on first OAuth login and refreshed automatically
