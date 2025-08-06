from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader, PyPDFLoader,UnstructuredWordDocumentLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-large")
import os

def DocContent(path,file_type):
    """Load PDF and return combined content as a single Document object"""
    try:
        if file_type==".pdf":
            loader = PyPDFLoader(path)
        elif file_type==".txt":
            loader= TextLoader(path)
        else:
            loader=UnstructuredWordDocumentLoader(path)
        documents = loader.load()
        
        if not documents:
            return Document(page_content="No content found in the PDF")
    
        combined_content = "\n".join([doc.page_content for doc in documents])
        
       
        return Document(page_content=combined_content, metadata={"source": path, "total_pages": len(documents)})
        
    except Exception as e:
        return Document(page_content=f"Error loading PDF: {str(e)}")


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
            return Document(page_content="No content found in the document !!")
    
        combined_content = "\n".join([doc.page_content for doc in documents])
    
        doc=Document(page_content=combined_content, metadata={"source": path, "total_pages": len(documents)})

        if file_size<= 10* file_size:
            
            text_splitter = CharacterTextSplitter(
            separator="\n\n",
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
            is_separator_regex=False,
            )
            chunks = text_splitter.split_text(doc.page_content)
            
            documents = [Document(page_content=chunk, metadata={"source": path}) for chunk in chunks]
            
            db = Chroma.from_documents(documents=documents, embedding=embeddings_model)
            return db
        
    except Exception as e:
        return Document(page_content=f"Error loading PDF: {str(e)}")