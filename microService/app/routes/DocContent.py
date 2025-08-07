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
document_cache = {}
MAX_CACHE_SIZE = 3 


persist_directory="./local_chroma"

def clear_document_cache():
    """Clear all cached documents when new document is uploaded"""
    global document_cache
    document_cache.clear()
    print("Document cache cleared")
    
def DocContentChunker(path, file_type):
    try:
        # Create cache key based on file path and modification time
        file_mtime = os.path.getmtime(path)
        cache_key = f"{path}_{file_mtime}"
        
        # Check if we already have this document in cache
        if cache_key in document_cache:
            print(f"Using cached vector store for: {os.path.basename(path)}")
            return document_cache[cache_key]
        
        print(f"Creating new vector store for: {os.path.basename(path)}")
        
        # Your existing file processing logic
        file_size = os.path.getsize(path)
        
        if file_type == ".pdf":
            loader = PyPDFLoader(path)
        elif file_type == ".txt":
            loader = TextLoader(path)
        else:
            loader = UnstructuredWordDocumentLoader(path)
            
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

            # Create in-memory vector store (faster, no disk I/O)
            db = Chroma.from_documents(
                documents=chunk_docs, 
                embedding=embeddings_model
                # No persist_directory = in-memory only
            )
            
            # Cache management: remove oldest if cache is full
            if len(document_cache) >= MAX_CACHE_SIZE:
                oldest_key = next(iter(document_cache))  # Get first (oldest) key
                del document_cache[oldest_key]
                print(f"Removed oldest cached document from memory")
            
            # Cache the new vector store
            document_cache[cache_key] = db
            print(f"Cached vector store. Cache size: {len(document_cache)}")
            
            return db
        
    except Exception as e:
        raise RuntimeError(f"Error loading file: {str(e)}")