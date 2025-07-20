import os
from dotenv import load_dotenv
load_dotenv()
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate


from langchain_openai import ChatOpenAI
from routes.DocContent import DocContent

llm = ChatOpenAI(model="gpt-4o-mini",temperature=0.2)





async def summary(path,file_type):
    """Generate summary from file content"""
    prompt_summary = ChatPromptTemplate.from_messages(
    [("system", """You are an expert educator skilled in analyzing educational content and summarizing it clearly and briefly.

        **Task:**  
        Generate a summary of the provided document where each chapter is summarized in 2 to 3 lines. 

**Formatting Guidelines:**  
- give a title to the summary and a abstract of the summary
- Use a numbered list (e.g., Chapter 1, Chapter 2, etc.).  
- For each chapter, provide a concise 2–3 line explanation of its key ideas.  
- Keep the language clear and student-friendly, suitable for quick reading and revision.  
- Do not include markdown or bullet points — just numbered chapters and summaries.
- if there is only 1 chapter available give a 10-12 line summary directly dont use the below format then
Example Output Format:
Chapter 1: [summary]
Chapter 2: [summary]
...

Document:
{context}""")]
)


    doc = DocContent(path,file_type)
    
    docs = [doc]
    
    chain = create_stuff_documents_chain(llm, prompt_summary)
    result = await chain.ainvoke({"context": docs})
    return result

