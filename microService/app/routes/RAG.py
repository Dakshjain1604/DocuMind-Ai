
from langchain_openai import ChatOpenAI

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from .DocContent import DocContentChunker
from routes.utils import count_tokens


llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)



prompt_template = PromptTemplate(
    input_variables=["context", "question"],
    template="""
    Use the following context to answer the question at the end in a well structed and readable answer feel free to consice it if it is too long.
    If the answer is not in the context, just say "I couldn’t find that in the document."

    Context:
    {context}

    Question: {question}
    Answer:
    """
    )


qa_chain = LLMChain(llm=llm, prompt=prompt_template)

async def RAG(path, file_type, input_query):
    db = DocContentChunker(path, file_type)
    if db is None:
        return "Error loading document or it exceeds the size limit."

    retriever = db.as_retriever(search_type="mmr", search_kwargs={"k": 5, "fetch_k": 10})
    docs = retriever.get_relevant_documents(input_query)
    max_context_tokens = 13500
    model_name = "gpt-3.5-turbo"
    selected_context = ""
    
    for doc in docs:
        new_context = selected_context + "\n\n" + doc.page_content
        if count_tokens(new_context, model_name) > max_context_tokens:
            break
        selected_context = new_context

 
    response = qa_chain.run({"context": selected_context, "question": input_query})
    return response






