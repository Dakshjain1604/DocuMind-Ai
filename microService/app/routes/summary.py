from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from app.routes.DocContent import DocContentChunker
from app.routes.utils import count_tokens  # You must define this
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

    db = DocContentChunker(path, file_type)
    retrieved_docs = db.similarity_search("summarize this", k=3)




    chain = create_stuff_documents_chain(llm, prompt_summary)
    result = await chain.ainvoke({"context": retrieved_docs})
    return result
