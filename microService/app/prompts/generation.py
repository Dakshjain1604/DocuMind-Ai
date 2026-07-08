"""Prompts for the final LLM generation step across /query, /summary, /quiz —
all three read indexed content and produce one user-facing block of text."""
from __future__ import annotations


ANSWER_PROMPT = """Answer the question using the numbered passages below.

CITATION RULES (strict):
- For every factual claim, cite the passage with ASCII square brackets like [1] or [2].
- Multiple sources in one citation: [1,3].
- DO NOT use full-width brackets 【 】 or parentheses ( ) for citations.
- Always use the plain ASCII characters [ and ].

OTHER RULES:
- If the answer is not in the passages, say "I couldn't find that in the document."
- Be concise. Don't repeat the question.

Passages:
{context}

Question: {question}

Answer:"""


DOCUMENT_SUMMARY_PROMPT = """Summarize the document. Output rules:

- Give a short title and a 1-sentence abstract.
- If the document has chapters, list each chapter with a 2-3 line summary (numbered).
- Otherwise give a 10-12 line summary with main points as a short list.
- No markdown fences. No leading prose.

Document content:
{content}
"""


QUIZ_PROMPT = """Generate exactly 12 multiple-choice questions from the document content.

Rules:
- Each question has exactly 4 options.
- correct_answer must match one of the options character-for-character.
- Questions 1-3 easy; 4-9 medium; 10-12 hard.
- Cover different aspects of the content.

Return JSON of the form:
{{"quiz": [{{"id":1,"question":"...","options":["A","B","C","D"],"correct_answer":"B","explanation":"..."}}]}}

Document content:
{content}
"""
