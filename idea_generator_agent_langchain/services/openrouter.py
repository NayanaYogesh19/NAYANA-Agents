import os

from dotenv import load_dotenv

from langchain_openai import ChatOpenAI

load_dotenv()


def get_llm():
    """
    Equivalent to the n8n OpenRouter Chat Model node.
    Returns the OpenRouter GPT-4o-mini model.
    """

    llm = ChatOpenAI(
        model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        temperature=0
    )

    return llm