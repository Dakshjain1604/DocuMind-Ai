from routes.DocContent import DocContent
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.text_splitter import CharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableMap
from langchain.chains import LLMChain


# Set up embeddings and LLM
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-large")
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)

# Define your custom prompt
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

# Build the custom LLMChain
qa_chain = LLMChain(llm=llm, prompt=prompt_template)

async def RAG(path, file_type, input_query):
    # Load document content
    doc = DocContent(path, file_type)
    #returs a string 
    if not doc.page_content or doc.page_content.startswith("Error"):
        return "Error loading document or no content found."

    # Split the text
    #chunks -- iufhaisdlhuqairfugwifgiwfgiwefgiUFGiweugfliweufg aiofgoawiufgqifgaskidfgqiuyrfgeqriwfg
    text_splitter = CharacterTextSplitter(
        separator="\n\n",
        chunk_size=500,
        chunk_overlap=50,
        length_function=len,
        is_separator_regex=False,
    )
    chunks = text_splitter.split_text(doc.page_content)

    # Convert chunks to LangChain Document objects
    documents = [Document(page_content=chunk, metadata={"source": path}) for chunk in chunks]

    # Create vector store
    db = Chroma.from_documents(documents=documents, embedding=embeddings_model)
    retriever = db.as_retriever()

    # Get relevant documents
    relevant_docs = retriever.invoke(input_query)

    # Concatenate contexts
    context = "\n\n".join([doc.page_content for doc in relevant_docs])

    # Run custom chain
    answer = qa_chain.run({"context": context, "question": input_query})
    return answer





