from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader, PyPDFLoader,UnstructuredWordDocumentLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings



load_dotenv()

embeddings_model = OpenAIEmbeddings(
    model="text-embedding-3-large",
    openai_api_key=os.getenv("OPENAI_API_KEY")
)



persist_directory="./local_chroma"
def DocContentChunker(path,file_type):
    try:
        file_size=os.path.getsize(path)

        if file_type==".pdf":
            loader = PyPDFLoader(path)
        elif file_type==".txt":
            loader= TextLoader(path)
        else:
            loader=UnstructuredWordDocumentLoader(path)
        documents = loader.load()
        
        if not documents:
            raise ValueError("No content found in the document !!")
    
        combined_content = "\n".join([doc.page_content for doc in documents])
        doc = Document(page_content=combined_content, metadata={"source": path, "total_pages": len(documents)})

        if file_size <= 10 * 1024 * 1024:
            text_splitter = CharacterTextSplitter(
                separator="\n\n",
                chunk_size=500,
                chunk_overlap=50,
                length_function=len,
                is_separator_regex=False,
            )
            chunks = text_splitter.split_text(doc.page_content)
            chunk_docs = [Document(page_content=chunk, metadata={"source": path}) for chunk in chunks]

            # Load or create Chroma
            if os.path.exists(persist_directory):
                db = Chroma(persist_directory=persist_directory, embedding_function=embeddings_model)
                db.add_documents(chunk_docs)
            else:
                db = Chroma.from_documents(documents=chunk_docs, embedding=embeddings_model, persist_directory=persist_directory)

            return db
        
    except Exception as e:
        raise RuntimeError(f"Error loading file: {str(e)}")