import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from .config import GEMINI_MODEL

load_dotenv()


class MissingApiKey(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_llm():
    key = os.getenv("GOOGLE_API_KEY")
    if not key or key.startswith("your-"):
        raise MissingApiKey(
            "GOOGLE_API_KEY is not set. Copy .env.example to .env and add your Gemini key."
        )
    # temperature 0 - we want faithful SQL and grounded answers, not creative ones
    return ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0, google_api_key=key)


def ask(messages):
    """Send a list of (role, content) tuples and return the text reply."""
    return get_llm().invoke(messages).content.strip()
