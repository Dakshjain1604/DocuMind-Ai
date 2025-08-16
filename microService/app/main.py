from typing import Annotated
import uvicorn
import aiofiles
from fastapi import FastAPI, File, UploadFile ,  Form
import os
from fastapi.middleware.cors import CORSMiddleware
from routes.summary import summary
from routes.quiz import generate_quiz_cards
from routes.RAG import RAG
from routes.DocContent import clear_document_cache
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def getFileLocation(file: UploadFile = File(...)):

    file_location = f"{UPLOAD_DIR}/{file.filename}"
    file_type=os.path.splitext(file.filename)[1].lower()
    clear_document_cache()
    async with aiofiles.open(file_location,"wb")as buffer:
        content=await file.read()
        await buffer.write(content)
        return {
            "file_location":file_location,
            "file_type":file_type
        }
    
@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI backend!"}

UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)  

@app.post("/getSummary")
async def GetSummary(file: UploadFile = File(...)):
    path =await getFileLocation(file) 
    file_path=path["file_location"]
    file_type=path["file_type"]
    result =await summary(file_path,file_type) 
    return {"filename": file.filename, "summary": result, "status": "completed"}

@app.post("/getQuiz")
async def GetQuiz(file: UploadFile = File(...)):
    path =await getFileLocation(file) 
    file_path=path["file_location"]
    file_type=path["file_type"]
    result =await generate_quiz_cards(file_path,file_type)
    return {"filename": file.filename, "summary": result, "status": "completed"}

@app.post('/RAG')
async def CustomQandA(file: UploadFile = File(...),
    input: str = Form(...)
    ):
    path= await getFileLocation(file)
    file_path=path["file_location"]
    file_type=path["file_type"]
    input=input
    result=await RAG(file_path,file_type,input)
    return {"answer": result}
    
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)