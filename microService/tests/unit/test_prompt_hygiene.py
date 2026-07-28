"""A JSON schema example must not contain usable content.

Every generation prompt shows the model the JSON shape it should return. When
those examples were filled in with realistic sample content rather than
placeholders, an 8B model copied them straight into its output:

  * /quiz returned "What is the main purpose of data orchestration?" with an
    explanation about Airflow and DAGs, as question 1, for a document about
    payment routing.
  * /compliance-audit returned "Plaintext credentials identified in
    configuration section" as a HIGH-severity finding against a document
    stating that credentials are tokenised and never stored in plaintext.

Both were observed against a live model, not hypothesised. These tests pin the
examples to placeholder form so the same regression cannot return quietly.
"""
import re

import pytest

from app.prompts.generation import (
    CHAPTER_EXTRACTOR_PROMPT,
    CHAPTER_QUIZ_PROMPT,
    COMPLIANCE_AUDIT_PROMPT,
    LEARNING_DRAFT_PROMPT,
    QUIZ_PROMPT,
    SLIDE_DECK_PROMPT,
)

ALL_PROMPTS = {
    "QUIZ_PROMPT": QUIZ_PROMPT,
    "COMPLIANCE_AUDIT_PROMPT": COMPLIANCE_AUDIT_PROMPT,
    "CHAPTER_EXTRACTOR_PROMPT": CHAPTER_EXTRACTOR_PROMPT,
    "CHAPTER_QUIZ_PROMPT": CHAPTER_QUIZ_PROMPT,
    "SLIDE_DECK_PROMPT": SLIDE_DECK_PROMPT,
    "LEARNING_DRAFT_PROMPT": LEARNING_DRAFT_PROMPT,
}

# Phrases that were previously copied verbatim into user-visible output.
LEAKED_EXAMPLES = [
    "data orchestration",
    "Airflow",
    "DAG execution",
    "unstructured binary video",
    "manually compile Python",
    "Plaintext credentials identified",
    "Migrate secrets to KMS",
    "Principles of Data System Architecture",
    "Data Ingestion / Input",
    "Core Processing & Engine",
]


@pytest.mark.parametrize("name,prompt", sorted(ALL_PROMPTS.items()))
def test_prompt_contains_no_previously_leaked_example(name, prompt):
    for phrase in LEAKED_EXAMPLES:
        assert phrase.lower() not in prompt.lower(), (
            f"{name} reintroduces sample content that a model will copy verbatim: {phrase!r}. "
            "Use a <placeholder> instead."
        )


@pytest.mark.parametrize(
    "name,prompt",
    [(n, p) for n, p in sorted(ALL_PROMPTS.items()) if "Return JSON" in p],
)
def test_json_schema_examples_use_placeholders(name, prompt):
    """Every string value in a schema example should be a <placeholder>."""
    # The schema line is the one containing the doubled braces of a JSON example.
    schema_lines = [ln for ln in prompt.splitlines() if '{{"' in ln]
    assert schema_lines, f"{name} has no recognisable JSON schema example"
    for line in schema_lines:
        # Values are either "<placeholder>", a format field, or a numeric id.
        for value in re.findall(r':\s*"([^"]*)"', line):
            assert value.startswith("<") and value.endswith(">"), (
                f"{name} schema example has literal value {value!r}; "
                "models copy these into real output. Use <placeholder> form."
            )


def test_answer_prompt_is_split_into_system_and_user():
    """The grounding contract belongs in a system turn - see ANSWER_SYSTEM_PROMPT."""
    from app.prompts.generation import ANSWER_SYSTEM_PROMPT, ANSWER_USER_PROMPT

    assert "{context}" not in ANSWER_SYSTEM_PROMPT
    assert "{question}" not in ANSWER_SYSTEM_PROMPT
    assert "{context}" in ANSWER_USER_PROMPT
    assert "{question}" in ANSWER_USER_PROMPT


def test_learning_draft_documents_mermaid_node_syntax():
    """Bare multi-word node ids are a parse error that loses the whole diagram."""
    assert "[square brackets]" in LEARNING_DRAFT_PROMPT
    assert "SomeNode[Some Node Name]" in LEARNING_DRAFT_PROMPT
