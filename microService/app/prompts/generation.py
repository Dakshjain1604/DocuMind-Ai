"""Prompts for the final LLM generation step across /query, /summary, /quiz, /compliance-audit, /audio-briefing, /slide-deck —
all read indexed content and produce clean structured outputs."""
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


DOCUMENT_SUMMARY_PROMPT = """You are an expert executive document summarizer. Create an exceptionally structured, highly readable summary of the document below using exact Markdown formatting tags.

Structure your response using these EXACT markdown prefixes:

# Executive Summary: [Document Title / Topic]

> **Executive Abstract**: Provide a crisp, 2-3 sentence high-level overview of the document's core thesis, context, and purpose.

---

## Key Takeaways & Core Concepts
- **[Concept 1 Name]**: Detailed explanation of the primary takeaway or key topic.
- **[Concept 2 Name]**: Detailed explanation of key findings or methodologies.
- **[Concept 3 Name]**: Detailed explanation of operational details, skills, or findings.
- **[Concept 4 Name]**: Additional core highlights with **bold emphasis** on metrics and technical terms.

---

## Section & Structural Breakdown
1. **[Section / Topic 1 Header]**
   - Key details, methodologies, or findings in this section.
2. **[Section / Topic 2 Header]**
   - Key details, methodologies, or findings in this section.
3. **[Section / Topic 3 Header]**
   - Key details, methodologies, or findings in this section.

---

## Practical Impact & Takeaways
- A concluding 2-sentence synthesis explaining the overall significance and practical application of this document.

Document content:
{content}
"""


QUIZ_PROMPT = """Generate exactly {n_questions} multiple-choice questions from the document content.

Rules:
- Each question MUST have exactly 4 full-sentence options.
- DO NOT use single-letter placeholders like "A", "B", "C", "D" as options! Every option in the array MUST be a complete, realistic answer choice.
- correct_answer MUST match one of the 4 full option text strings character-for-character.
- Provide a balanced progression from easy to medium to hard difficulty across the {n_questions} questions.
- Cover different chapters, topics, and technical details of the content.

Return JSON of the form:
{{"quiz": [{{"id": 1, "question": "What is the main purpose of data orchestration?", "options": ["To schedule and coordinate pipeline workflows across nodes", "To store unstructured binary video files", "To disable network security and access controls", "To manually compile Python code line by line"], "correct_answer": "To schedule and coordinate pipeline workflows across nodes", "explanation": "Data orchestration frameworks like Airflow manage and automate DAG execution workflows."}}]}}

Document content:
{content}
"""


CHAPTER_EXTRACTOR_PROMPT = """Analyze the document headings and content outline below. Extract or divide the document into 4 to 8 logical Chapters or Masterclass Modules.

Return JSON of the form:
{{"chapters": [{{"id": 1, "title": "Chapter 1: Principles of Data System Architecture", "summary": "Covers core security models, scalability, and system bounds."}}]}}

Document Outline / Passages:
{content}
"""


LEARNING_DRAFT_PROMPT = """You are a world-class principal software architect and educator. Create an exceptionally clear, visual **Masterclass Learning Draft** for "{chapter_title}" using the document content below.

CRITICAL REQUIREMENT: You MUST include an explicit ```mermaid architecture diagram code block in section 2 below. DO NOT omit the mermaid block!

Structure your response using these EXACT sections:

# Masterclass Learning Draft: {chapter_title}

> **Executive Core Thesis**: Provide a crisp 2-sentence summary of what the student will master in this module.

---

## Interactive System Architecture Diagram
You MUST output a valid ```mermaid code block visualising data flows, components, or concept relationships for this chapter:
```mermaid
graph TD
    A[Data Ingestion / Input] --> B[Core Processing & Engine]
    B --> C[Storage / Analytics Layer]
    B --> D[Security & Control Pipeline]
```

---

## Core Technical Mechanics & Deep Dive
- **[Concept 1]**: Detailed technical explanation with **bold keywords**.
- **[Concept 2]**: Detailed technical explanation with code/math snippets if applicable.
- **[Concept 3]**: Detailed technical explanation of internal mechanics.

---

## Engineering Tradeoffs & Industry Best Practices
- **Tradeoff Analysis**: Compare key architectural decisions (e.g., Consistency vs Availability, Push vs Pull).
- **Production Tip**: 2 actionable guidelines for real-world production deployment.

Document Content for {chapter_title}:
{content}
"""


CHAPTER_QUIZ_PROMPT = """Generate exactly 5 targeted multiple-choice questions specifically testing comprehension of "{chapter_title}".

Rules:
- Each question MUST have exactly 4 full-sentence options.
- DO NOT use single-letter placeholders like "A", "B", "C", "D" as options! Every option in the array MUST be a complete, realistic answer choice.
- correct_answer MUST match one of the 4 full option text strings character-for-character.
- Range from easy to hard difficulty.

Return JSON of the form:
{{"quiz": [{{"id": 1, "question": "...", "options": ["Option 1 text", "Option 2 text", "Option 3 text", "Option 4 text"], "correct_answer": "Option 1 text", "explanation": "..."}}]}}

Chapter Content for {chapter_title}:
{content}
"""


COMPLIANCE_AUDIT_PROMPT = """Analyze the document content below as a principal security and compliance auditor. Identify 3 to 6 key operational, security, or compliance risks/insights.

Assign a risk severity level ("high", "medium", "low") to each item.

Return JSON of the form:
{{"audit": [{{"id": 1, "severity": "high", "category": "Data Encryption", "finding": "Plaintext credentials identified in configuration section", "mitigation": "Migrate secrets to KMS / Key Vault and enforce TLS 1.3"}}]}}

Document content:
{content}
"""


AUDIO_BRIEFING_PROMPT = """Create an exceptionally engaging, 2-host executive podcast script ("Alex" and "Morgan") discussing the document content below.

Format:
# Executive Podcast Briefing: {title}

**Alex**: Welcome back. Today we are diving into...
**Morgan**: Exactly, Alex. What stands out immediately is...

Keep the conversation crisp, analytical, and professional. 4 to 8 alternating dialogue turns.

Document content:
{content}
"""


SLIDE_DECK_PROMPT = """Generate a 5-slide executive presentation deck based on the document content.

Return JSON of the form:
{{"slides": [{{"slide": 1, "title": "Executive Overview & Thesis", "bullets": ["Bullet point 1", "Bullet point 2", "Bullet point 3"], "speaker_notes": "Key takeaway for presenter."}}]}}

Document content:
{content}
"""
