"""Summary generation — reuses indexed artifacts."""
from app.core.llm import get_llm
from app.indexing.store import load_artifacts, artifacts_exist


SUMMARY_PROMPT = """Summarize the document. Output rules:

- Give a short title and a 1-sentence abstract.
- If the document has chapters, list each chapter with a 2-3 line summary (numbered).
- Otherwise give a 10-12 line summary with main points as a short list.
- No markdown fences. No leading prose.

Document content:
{content}
"""


async def summarize(doc_hash: str) -> str:
    if not artifacts_exist(doc_hash):
        raise FileNotFoundError(f"doc_hash {doc_hash} not indexed")
    loaded = load_artifacts(doc_hash)
    from langchain_chroma import Chroma
    from app.core.embeddings import get_embeddings

    chroma = Chroma(persist_directory=loaded["chroma_dir"], embedding_function=get_embeddings())
    res = chroma.get(include=["documents"])
    content = "\n\n".join(res.get("documents", [])[:8])  # cap to keep prompt size sane

    r = await get_llm().complete(
        role="answer",
        messages=[{"role": "user", "content": SUMMARY_PROMPT.format(content=content)}],
        temperature=0.2,
    )
    return r.content
