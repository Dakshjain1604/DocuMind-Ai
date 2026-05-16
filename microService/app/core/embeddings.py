"""Embedding model — OpenAI text-embedding-3-large, used by Chroma."""
import os
from functools import lru_cache
from langchain_openai import OpenAIEmbeddings


@lru_cache(maxsize=1)
def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model="text-embedding-3-large",
        openai_api_key=os.environ["OPENAI_API_KEY"],
    )
