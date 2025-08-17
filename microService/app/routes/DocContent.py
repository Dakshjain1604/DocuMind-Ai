from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader, PyPDFLoader, UnstructuredWordDocumentLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
import os
import shutil
from dotenv import load_dotenv

load_dotenv()

embeddings_model = OpenAIEmbeddings(
    model="text-embedding-3-large",
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

document_cache = {}
MAX_CACHE_SIZE = 3 
persist_directory = "./local_chroma"

# -----------------------------
# Cache clearing functions
# -----------------------------
def clear_document_cache():
    """Clear in-memory cache"""
    global document_cache
    document_cache.clear()
    print("Document cache cleared")

def clear_chroma_cache():
    """Delete persisted Chroma DB"""
    if os.path.exists(persist_directory):
        shutil.rmtree(persist_directory)
        print("Chroma cache cleared from disk")

def clear_all_cache():
    """Clear both in-memory + disk cache"""
    clear_document_cache()
    clear_chroma_cache()

# -----------------------------
# Main document processing
# -----------------------------
def DocContentChunker(path, file_type):
    try:
        # Always clear old cache when a new file is uploaded
        clear_all_cache()

        file_mtime = os.path.getmtime(path)
        cache_key = f"{path}_{file_mtime}"
        
        if cache_key in document_cache:
            print(f"Using cached vector store for: {os.path.basename(path)}")
            return document_cache[cache_key]
        
        print(f"Creating new vector store for: {os.path.basename(path)}")
        
        file_size = os.path.getsize(path)
        
        # Choose loader
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

        if file_size <= 10 * 1024 * 1024:  # 10 MB limit
            text_splitter = CharacterTextSplitter(
                separator="\n\n",
                chunk_size=500,
                chunk_overlap=50,
                length_function=len,
                is_separator_regex=False,
            )
            chunks = text_splitter.split_text(doc.page_content)
            chunk_docs = [Document(page_content=chunk, metadata={"source": path}) for chunk in chunks]

            db = Chroma.from_documents(
                documents=chunk_docs, 
                embedding=embeddings_model,
                persist_directory=persist_directory  # Now persist
            )
            
            db.persist()  # Save to disk
            
            # Update in-memory cache
            if len(document_cache) >= MAX_CACHE_SIZE:
                oldest_key = next(iter(document_cache))
                del document_cache[oldest_key]
                print(f"Removed oldest cached document from memory")
            
            document_cache[cache_key] = db
            print(f"Cached vector store. Cache size: {len(document_cache)}")
            
            return db
        
    except Exception as e:
        raise RuntimeError(f"Error loading file: {str(e)}")
