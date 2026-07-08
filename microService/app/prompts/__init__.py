"""All LLM prompt templates for the served app, grouped by pipeline stage so
each is easy to find and tune without touching pipeline/retrieval logic:

- indexing.py:   graph extraction, community summarization (used by /index)
- retrieval.py:  query rewrite, LLM rerank (used by /query's retrieval stage)
- generation.py: final answer/summary/quiz generation (/query, /summary, /quiz)

Offline tooling prompts (tuning/build_eval_set.py) intentionally stay in
tuning/ — they aren't part of the served app.
"""
from app.prompts.indexing import COMMUNITY_SUMMARY_PROMPT, EXTRACTION_PROMPT
from app.prompts.retrieval import RERANK_PROMPT, REWRITE_PROMPT
from app.prompts.generation import ANSWER_PROMPT, DOCUMENT_SUMMARY_PROMPT, QUIZ_PROMPT

__all__ = [
    "COMMUNITY_SUMMARY_PROMPT",
    "EXTRACTION_PROMPT",
    "RERANK_PROMPT",
    "REWRITE_PROMPT",
    "ANSWER_PROMPT",
    "DOCUMENT_SUMMARY_PROMPT",
    "QUIZ_PROMPT",
]
