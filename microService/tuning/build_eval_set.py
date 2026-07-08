"""Build evaluation set by generating synthetic questions from PDF chunks.

Question generation is cached transparently by app.core.llm.LLMClient's
shared LLM-response cache (keyed on role+messages+temperature) — re-running
this script only pays for chunks whose question hasn't been generated
before, no bespoke cache needed here.
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.documents import Document
from app.core.chunker import chunk_documents
from app.core.llm import get_llm, LLMRoleNotConfigured

PDF_PATH = Path("tmp/uploaded_files/AI Engineering.pdf")
EVAL_SET_PATH = Path("microService/tuning/eval_set.jsonl")
NUM_QUESTIONS = 40
MIN_CHUNK_LENGTH = 200
CONCURRENCY_LIMIT = 4

QUESTION_GEN_PROMPT = """You are given a passage from a document about AI Engineering.

Your task: Generate ONE specific factual question whose answer can be found ONLY in this passage.
The question should:
- Be answerable using ONLY the information in this passage
- Be specific enough that the answer is unambiguous
- NOT reference information from outside this passage
- Be a natural question someone might ask about this content

Passage:
{chunk_text}

Generate only the question, nothing else. The question should be 1-2 sentences maximum."""


def load_pdf_documents(pdf_path: Path) -> list[Document]:
    print(f"Loading PDF: {pdf_path}")
    
    try:
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(str(pdf_path))
        docs = loader.load()
        print(f"Loaded {len(docs)} pages using PyPDFLoader")
        return docs
    except Exception as e:
        print(f"PyPDFLoader failed: {e}")
    
    try:
        import pypdf
        docs = []
        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text.strip():
                    docs.append(Document(page_content=text, metadata={"page": i + 1}))
        print(f"Loaded {len(docs)} pages using pypdf")
        return docs
    except Exception as e:
        print(f"pypdf fallback failed: {e}")
        raise RuntimeError(f"Could not load PDF from {pdf_path}")


async def generate_question_for_chunk(
    llm: Any,
    chunk: Document,
    semaphore: asyncio.Semaphore,
    progress: dict,
) -> dict[str, Any] | None:
    chunk_text = chunk.page_content
    chunk_id = chunk.metadata.get("chunk_id", -1)

    async with semaphore:
        try:
            prompt = QUESTION_GEN_PROMPT.format(chunk_text=chunk_text)
            result = await llm.complete(
                role="rewrite",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            question = result.content.strip()

            progress["completed"] += 1
            print(f"  [{progress['completed']}/{progress['total']}] Generated Q for chunk {chunk_id}")
            
            return {
                "question": question,
                "gold_chunk_id": chunk_id,
                "gold_chunk_text": chunk_text,
            }
        except Exception as e:
            progress["completed"] += 1
            print(f"  [{progress['completed']}/{progress['total']}] ERROR for chunk {chunk_id}: {e}")
            return None


async def build_eval_set() -> None:
    print("=" * 60)
    print("Building Evaluation Set for GraphRAG Tuning")
    print("=" * 60)
    
    EVAL_SET_PATH.parent.mkdir(parents=True, exist_ok=True)

    docs = load_pdf_documents(PDF_PATH)
    
    print("\nChunking documents...")
    chunks = chunk_documents(docs, chunk_size=1000, chunk_overlap=150)
    print(f"Created {len(chunks)} chunks")
    
    valid_chunks = [c for c in chunks if len(c.page_content) >= MIN_CHUNK_LENGTH]
    print(f"Chunks >= {MIN_CHUNK_LENGTH} chars: {len(valid_chunks)}")
    
    if len(valid_chunks) < NUM_QUESTIONS:
        print(f"WARNING: Only {len(valid_chunks)} valid chunks, using all of them")
        sampled_chunks = valid_chunks
    else:
        random.seed(42)
        sampled_chunks = random.sample(valid_chunks, NUM_QUESTIONS)
        print(f"Sampled {NUM_QUESTIONS} chunks for question generation")
    
    print("\nInitializing OpenRouter LLM...")
    try:
        llm = get_llm()
        print("LLM initialized successfully")
    except LLMRoleNotConfigured as e:
        print(f"ERROR: LLM role not configured: {e}")
        print("Please set OPENROUTER_MODEL_REWRITE environment variable")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR initializing LLM: {e}")
        sys.exit(1)
    
    print(f"\nGenerating questions (concurrency={CONCURRENCY_LIMIT})...")
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    progress = {"completed": 0, "total": len(sampled_chunks)}

    tasks = [
        generate_question_for_chunk(llm, chunk, semaphore, progress)
        for chunk in sampled_chunks
    ]
    results = await asyncio.gather(*tasks)

    eval_items = [r for r in results if r is not None]

    print(f"\nGenerated {len(eval_items)} questions")

    print(f"\nSaving to {EVAL_SET_PATH}")
    with open(EVAL_SET_PATH, "w") as f:
        for item in eval_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Evaluation set saved: {EVAL_SET_PATH}")
    print(f"  Total questions: {len(eval_items)}")


if __name__ == "__main__":
    # Load credentials
    cred_path = Path.home() / ".neo" / "integrations" / "openrouter.env"
    if cred_path.exists():
        with open(cred_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    if key == "api_key":
                        os.environ.setdefault("OPENROUTER_API_KEY", value)
                    else:
                        os.environ.setdefault(key, value)
    
    if not os.environ.get("OPENROUTER_MODEL_REWRITE"):
        os.environ["OPENROUTER_MODEL_REWRITE"] = "anthropic/claude-haiku-4.5,openai/gpt-4o-mini"
    
    asyncio.run(build_eval_set())
