from fastapi import APIRouter
from pydantic import BaseModel

from services.metrics_service import calculate_metrics
from services.db_service import save_faqs
from services.scraper_service import extract_website_content

from services.llm_service import (
    test_llm,
    generate_plan,
    generate_questions,
    generate_answers
)

router = APIRouter()


# -----------------------------------
# REQUEST MODEL
# -----------------------------------
class AnswerRequest(BaseModel):
    questions: list
    url: str


# -----------------------------------
# TEST SCRAPER
# -----------------------------------
@router.get("/test-scraper")
def test_scraper(url: str):

    data = extract_website_content(url)

    return {
        "preview": data[:1000]
    }


# -----------------------------------
# TEST LLM
# -----------------------------------
@router.get("/test-llm")
def test_llm_api():

    return {
        "output": test_llm()
    }


# -----------------------------------
# GENERATE PLAN
# -----------------------------------
@router.get("/generate-plan")
def generate_plan_api(url: str, topic: str):

    plan = generate_plan(url, topic)

    return {

        "url": url,

        "topic": topic,

        "plan": plan

    }


# -----------------------------------
# GENERATE QUESTIONS
# -----------------------------------
@router.get("/generate-questions")
def generate_questions_api(url: str, topic: str):

    print("STEP 1 → QUESTION REQUEST RECEIVED")

    # Step 1 → Scrape website content
    content = extract_website_content(url)

    print("STEP 2 → SCRAPING DONE")

    # Step 2 → Generate questions
    questions = generate_questions(
        content,
        topic
    )

    print("STEP 3 → QUESTIONS GENERATED")

    print("QUESTIONS:", questions)

    return {

        "url": url,

        "topic": topic,

        "questions": questions

    }


# -----------------------------------
# GENERATE ANSWERS
# -----------------------------------
@router.post("/generate-answers")
def generate_answers_api(request: AnswerRequest):

    print("STEP 1 → REQUEST RECEIVED")

    # Step 1 → Scrape website content
    content = extract_website_content(
        request.url
    )

    print("STEP 2 → SCRAPING DONE")

    # Step 2 → Generate answers
    faq_answers = generate_answers(

        request.questions,
        content

    )

    print("STEP 3 → ANSWERS GENERATED")

    print("FAQ ANSWERS:", faq_answers)

    # Step 3 → Save FAQs to Supabase
    response = save_faqs(

        request.url,

        "FAQ Optimization",

        faq_answers.get("faq", [])

    )

    print("SUPABASE RESPONSE:", response)

    print("STEP 4 → SAVED TO SUPABASE")

    # Step 4 → Calculate metrics
    metrics = calculate_metrics(
        faq_answers
    )

    print("STEP 5 → METRICS CALCULATED")

    print("METRICS:", metrics)

    # Step 5 → Return final response
    return {

        "faq": faq_answers.get("faq", []),

        "metrics": metrics

    }