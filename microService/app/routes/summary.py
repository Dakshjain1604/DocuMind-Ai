import os
from dotenv import load_dotenv
load_dotenv()
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from routes.DocContent import DocContent,DocContentChunker

llm = ChatOpenAI(model="gpt-3.5-turbo",temperature=0.2)

async def summary(path,file_type):
    """Generate summary from file content"""
    prompt_summary = ChatPromptTemplate.from_messages(
    [("system", """You are an expert educator skilled in analyzing educational content and summarizing it clearly and briefly.

        **Task:**  
        Generate a summary of the provided document where each chapter is summarized in 2 to 3 lines. 

**Formatting Guidelines:**  
- give a title to the summary and a abstract of the summary
- if it is a story ,Use a numbered list (e.g., Chapter 1, Chapter 2, etc.). else give pointers about the main contents of the text
- For each chapter, provide a concise 2–3 line explanation of its key ideas.  
- Keep the language clear and student-friendly, suitable for quick reading and revision.  
- Do not include markdown or bullet points — just numbered chapters and summaries.
- if there is only 1 chapter available give a 10-12 line summary directly dont use the below format then
Example Output Format if there are chapters available:
Chapter 1: [summary]
Chapter 2: [summary]
      
Example Output Format if the text is about some topic or has 1 full description
main Summary:[summary]
main Points-
        -
        -
        -
        -
        -
...

Document:
{context}""")]
)
    # doc = DocContent(path,file_type)

    # docs = [doc]
    db=DocContentChunker(path,file_type)
    docs=db.similarity_search("summarize this",k=4)
    chain = create_stuff_documents_chain(llm, prompt_summary)
    result = await chain.ainvoke({"context": docs})
    return result

