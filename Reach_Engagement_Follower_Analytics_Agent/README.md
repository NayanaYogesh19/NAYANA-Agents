
# Reach Engagement Follower Analytics Agent

A FastAPI-based social media analytics agent that scrapes public profile data from Instagram, Facebook, LinkedIn, and YouTube using Apify, then runs AI-powered analysis via OpenRouter to generate engagement insights and content strategy recommendations.

---

## Features

- Scrapes follower count, post count, bio, and engagement metrics from public social profiles
- Supports Instagram, Facebook, LinkedIn, and YouTube
- AI analysis (via OpenRouter / GPT-4o-mini) generates content angles, post types, target audience, brand tone, and recommended strategy
- Glassmorphism UI with light/dark mode toggle
- Summary card aggregating insights across all analyzed platforms

---

## Tech Stack

| Layer    | Technology                              |
|----------|-----------------------------------------|
| Backend  | FastAPI + Uvicorn                       |
| Scraping | Apify Client (Apify actors)             |
| AI       | OpenRouter API (GPT-4o-mini)            |
| Frontend | HTML + CSS (Glassmorphism) + Vanilla JS |

---

## Project Structure

```
Reach_Engagement_Follower_Analytics_Agent/
├── agents/
│   └── analytics_agent.py        # Orchestrates all scrapers
├── scrapers/
│   ├── instagram_scraper.py
│   ├── facebook_scraper.py
│   ├── linkedin_scraper.py
│   ├── linkedin_posts_scraper.py
│   ├── youtube_scraper.py
│   └── youtube_posts_scraper.py
├── services/
│   └── ai_analyzer.py            # OpenRouter AI analysis
├── utils/
│   └── analytics.py              # Summary generator
├── static/
│   ├── style.css                 # Trilliant glassmorphism theme
│   └── script.js                 # Frontend logic
├── templates/
│   └── index.html                # UI template
├── main.py                       # FastAPI app entry point
├── requirements.txt
├── run.bat
└── .env                          # API keys (not committed)
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create a `.env` file

```env
APIFY_API_TOKEN=your_apify_api_token_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

- **Apify token:** [console.apify.com](https://console.apify.com) → Settings → Integrations → API token
- **OpenRouter key:** [openrouter.ai/keys](https://openrouter.ai/keys) → Create Key

### 3. Run the agent

```bash
python -m uvicorn main:app --reload
```

Open `http://127.0.0.1:8000` in your browser.

---

## Usage

1. Enter one or more social media profile URLs in the input fields
2. Click **Analyze Profiles**
3. Results appear as cards showing:
   - Followers / subscribers / posts
   - Estimated average likes & comments
   - AI-generated content angles, post types, target audience, brand tone
   - Recommended strategy
   - Overall summary across all platforms

### Example Inputs

| Platform  | Example URL                              |
|-----------|------------------------------------------|
| Instagram | `https://www.instagram.com/nike/`        |
| Facebook  | `https://www.facebook.com/nike`          |
| LinkedIn  | `https://www.linkedin.com/company/nike`  |
| YouTube   | `https://www.youtube.com/@nike`          |

> You do not need to fill all four fields — analyze only the platforms you need.

---

## API

### `POST /analyze`

**Request body:**
```json
{
  "instagram_url": "https://www.instagram.com/nike/",
  "facebook_url": "",
  "linkedin_url": "",
  "youtube_url": ""
}
```

**Response:**
```json
{
  "instagram": {
    "platform": "Instagram",
    "followers": 306000000,
    "posts": 1200,
    "estimated_average_likes": "1500+",
    "estimated_average_comments": "150+",
    "post_types": ["Image Posts", "Reels"],
    "content_angles": ["Inspiration", "Product Showcase"],
    "target_audience": "Athletes and sports enthusiasts",
    "brand_tone": "Motivational",
    "recommended_strategy": ["Post consistently", "Use Reels for reach"]
  },
  "summary": {
    "total_platforms_analyzed": 1,
    "platforms": ["instagram"],
    "top_content_patterns": ["Inspiration", "Product Showcase"],
    "recommended_strategy": ["Post consistently", "Use Reels for reach"]
  }
}
```

---

## Notes

- `.env` is listed in `.gitignore` and will never be committed
- Only public profile URLs are supported — private accounts will return no data
- Apify actors used: `apify/instagram-profile-scraper`, `apify/facebook-pages-scraper`, and LinkedIn/YouTube equivalents

