from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader, PyPDFLoader,UnstructuredWordDocumentLoader

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
