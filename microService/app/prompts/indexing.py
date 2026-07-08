"""Prompts used during /index — graph extraction (per parent chunk) and
community summarization (per Louvain community)."""
from __future__ import annotations


EXTRACTION_PROMPT = """You extract a knowledge graph from a passage of text.

Return ONLY valid JSON matching this schema:
{
  "entities":      [{"id": "string", "type": "string", "description": "string"}],
  "relationships": [{"src": "string", "dst": "string", "type": "string", "description": "string"}]
}

Rules:
- entity id is the canonical name (e.g. "Mitochondria", not "the mitochondria")
- type is one of: Person, Organization, Concept, Process, Thing, Place, Event
- only include relationships where BOTH endpoints appear in entities
- be conservative — only include entities/relations actually stated in the passage

Passage:
"""


COMMUNITY_SUMMARY_PROMPT = """Summarize the following group of related concepts in 2-3 sentences.
Concepts:
{members}

Relationships:
{edges}

Summary:"""
