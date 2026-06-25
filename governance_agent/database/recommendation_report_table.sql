-- Run this in Supabase SQL Editor.

-- Step 1: Drop old table and recreate clean
DROP TABLE IF EXISTS recommendation_report;

CREATE TABLE recommendation_report (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name TEXT NOT NULL,
    isin_number  TEXT NOT NULL DEFAULT '',
    meeting_date TIMESTAMPTZ,
    "2022-23"    TEXT,
    "2023-24"    TEXT,
    "2024-25"    TEXT
);
