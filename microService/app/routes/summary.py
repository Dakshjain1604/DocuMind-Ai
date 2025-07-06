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
        [("system", """You are an expert professor skilled at simplifying complex information and creating clear, well-structured summaries. 

    **Task:**  
    Generate a concise, organized summary of the provided document with the following structure and  keep the summary size relative to the size of the document:  

    1. **Main Headings**: Identify and list the key topics.  
    2. **Explanation**: Briefly explain each topic in simple, easy-to-understand language.  
    3. **Real-World Examples**: Provide relevant examples or applications for each topic.  

    **Formatting Guidelines**:  
    - Use clear headings, bullet points, and numbering for structure.  
    - Avoid markdown (no **, ##, etc.). Use plain text with clear spacing/indentation.  
    - Ensure logical flow between topics.  

    **Output**: Return only the structured summary text, ready for easy reading.  

    Document:  
    {context}""")]
    )

    doc = DocContent(path,file_type)
    
    docs = [doc]
    
    chain = create_stuff_documents_chain(llm, prompt_summary)
    result = await chain.ainvoke({"context": docs})
    return result

