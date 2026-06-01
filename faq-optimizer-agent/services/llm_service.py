from langchain_openai import ChatOpenAI
from langsmith import Client
from config.settings import OPENROUTER_API_KEY

import json
import re
client = Client()

# -----------------------------------
# INITIALIZE LLM
# -----------------------------------

def get_llm():

    return ChatOpenAI(

        model="openai/gpt-4o-mini",

        openai_api_key=OPENROUTER_API_KEY,

        openai_api_base="https://openrouter.ai/api/v1",

        temperature=0.3
    )


# -----------------------------------
# SIMPLE TEST
# -----------------------------------

def test_llm():

    llm = get_llm()

    response = llm.invoke(
        "Say hello in one short sentence"
    )

    return response.content


# -----------------------------------
# GENERATE PLAN
# -----------------------------------

def generate_plan(url: str, topic: str):

    llm = get_llm()

    # Pull prompt from LangSmith
    prompt = client.pull_prompt(
    "nayana/faq-plan-prompt",
    include_model=False,

)

    formatted_prompt = prompt.invoke({

        "url": url,
        "topic": topic

    })

    response = llm.invoke(
        formatted_prompt
    )

    return response.content


# -----------------------------------
# GENERATE QUESTIONS
# -----------------------------------

def generate_questions(content: str, topic: str):

    llm = get_llm()

    # Pull prompt from LangSmith
    prompt = client.pull_prompt(
    "nayana/faq-question-prompt",
    include_model=False,
    
)

    formatted_prompt = prompt.invoke({

        "content": content,
        "topic": topic

    })

    response = llm.invoke(
        formatted_prompt
    )

    raw_output = response.content

    print("RAW QUESTIONS:", raw_output)

    try:

        return json.loads(raw_output)

    except Exception:

        match = re.search(
            r'\{.*\}',
            raw_output,
            re.DOTALL
        )

        if match:

            try:
                return json.loads(match.group())

            except Exception:
                pass

        return {

            "error": "Invalid JSON output",

            "raw_output": raw_output

        }


# -----------------------------------
# GENERATE ANSWERS
# -----------------------------------

def generate_answers(questions, content):

    llm = get_llm()

    try:

        answer_prompt = client.pull_prompt(
            "nayana/faq-answer-prompt",
            include_model=False
        )

        formatted_prompt = answer_prompt.invoke({
            "questions": questions,
            "content": content
        })

        response = llm.invoke(formatted_prompt)

        raw_output = response.content

        print("RAW ANSWERS:", raw_output)

        try:
            return json.loads(raw_output)

        except Exception:

            match = re.search(r'\{.*\}', raw_output, re.DOTALL)

            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass

        # fallback response
        faq_list = []

        for q in questions:

            if isinstance(q, dict):

                faq_list.append({
                    "question": q.get("question", ""),
                    "answer": "This information is currently being optimized based on the website content.",
                    "category": q.get("category", "General")
                })

        return {
            "faq": faq_list
        }

    except Exception as e:

        print("ANSWER GENERATION ERROR:", str(e))

        faq_list = []

        for q in questions:

            if isinstance(q, dict):

                faq_list.append({
                    "question": q.get("question", ""),
                    "answer": "Answer generation is temporarily unavailable.",
                    "category": q.get("category", "General")
                })

        return {
            "faq": faq_list
        }