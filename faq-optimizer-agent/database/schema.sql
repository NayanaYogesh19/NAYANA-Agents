CREATE TABLE IF NOT EXISTS faq_records (

    id BIGSERIAL PRIMARY KEY,

    company_name TEXT,

    website_url TEXT,

    topic TEXT,

    question TEXT,

    answer TEXT,

    category TEXT,

    created_at TIMESTAMP DEFAULT NOW()

);