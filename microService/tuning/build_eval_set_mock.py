"""Build mock evaluation set from PDF chunks (no LLM required)."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.documents import Document
from app.core.chunker import chunk_documents

PDF_PATH = Path("tmp/uploaded_files/AI Engineering.pdf")
EVAL_SET_PATH = Path("microService/tuning/eval_set.jsonl")
NUM_QUESTIONS = 40
MIN_CHUNK_LENGTH = 200


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


def generate_mock_question(chunk_text: str, chunk_id: int) -> str:
    """Generate a simple mock question based on chunk content."""
    # Extract first sentence or first 100 chars
    first_part = chunk_text[:200].strip()
    
    # Create a simple factual question based on content
    lines = chunk_text.split('\n')
    for line in lines:
        line = line.strip()
        if len(line) > 50 and not line.startswith('Figure') and not line.startswith('Table'):
            # Create a question about this line
            words = line.split()
            if len(words) > 5:
                # Extract key terms
                key_terms = [w for w in words if len(w) > 4 and w[0].isupper()][:3]
                if key_terms:
                    return f"What information is provided about {' '.join(key_terms[:2])}?"
    
    # Fallback
    return f"What does the document say about the content in section {chunk_id}?"


def build_mock_eval_set() -> None:
    print("=" * 60)
    print("Building Mock Evaluation Set for GraphRAG Tuning")
    print("(Using sample chunks without LLM - API credits unavailable)")
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
        print(f"Sampled {NUM_QUESTIONS} chunks for mock question generation")
    
    print("\nGenerating mock questions...")
    eval_items = []
    
    for i, chunk in enumerate(sampled_chunks, 1):
        chunk_id = chunk.metadata.get("chunk_id", -1)
        chunk_text = chunk.page_content
        
        question = generate_mock_question(chunk_text, chunk_id)
        
        eval_items.append({
            "question": question,
            "gold_chunk_id": chunk_id,
            "gold_chunk_text": chunk_text,
        })
        
        if i % 10 == 0:
            print(f"  Generated {i}/{len(sampled_chunks)} questions")
    
    print(f"\nGenerated {len(eval_items)} mock questions")
    
    print(f"\nSaving to {EVAL_SET_PATH}")
    with open(EVAL_SET_PATH, "w") as f:
        for item in eval_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    
    print(f"✓ Mock evaluation set saved: {EVAL_SET_PATH}")
    print(f"  Total questions: {len(eval_items)}")
    print(f"\nNOTE: This is a MOCK eval set for testing the sweep pipeline.")
    print(f"      For production use, generate questions with LLM API.")


if __name__ == "__main__":
    build_mock_eval_set()
