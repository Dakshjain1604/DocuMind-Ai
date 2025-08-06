from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from routes.DocContent import DocContentChunker
from routes.utils import count_tokens  # You must define this
import os
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2)

MAX_CONTEXT_TOKENS = 13500  # Leave margin for prompt & output

async def summary(path, file_type):
    """Generate summary from file content"""

    # Prompt for summarization
    prompt_summary = ChatPromptTemplate.from_messages([
        ("system", """You are an expert educator skilled in analyzing educational content and summarizing it clearly and briefly.

**Task:**  
Generate a summary of the provided document where each chapter is summarized in 2 to 3 lines.

**Formatting Guidelines:**  
- Give a title to the summary and an abstract of the summary.  
- If it is a story, use a numbered list (e.g., Chapter 1, Chapter 2, etc.). Otherwise, give pointers about the main contents of the text.  
- For each chapter, provide a concise 2–3 line explanation of its key ideas.  
- Keep the language clear and student-friendly, suitable for quick reading and revision.  
- Do not include markdown or bullet points — just numbered chapters and summaries.  
- If there is only 1 chapter available, give a 10–12 line summary directly.

**Example Output Format if there are chapters:**
Chapter 1: [summary]  
Chapter 2: [summary]  

**Example Output if single topic:**
Main Summary: [summary]  
Main Points -  
    -  
    -  
    -  
...  

Document:
{context}
""")
    ])

    # Retrieve document chunks
    db = DocContentChunker(path, file_type)
    retrieved_docs = db.similarity_search("summarize this", k=8)

    # Concatenate and trim context to stay within token limits
    selected_context = ""
    for doc in retrieved_docs:
        new_context = selected_context + "\n\n" + doc.page_content
        if count_tokens(new_context, model_name="gpt-3.5-turbo") > MAX_CONTEXT_TOKENS:
            break
        selected_context = new_context

    # Fallback in case no context fits
    if not selected_context.strip():
        selected_context = retrieved_docs[0].page_content[:5000]  # fallback slice

    # Chain + summary generation
    chain = create_stuff_documents_chain(llm, prompt_summary)
    result = await chain.ainvoke({"context": selected_context})
    return result
