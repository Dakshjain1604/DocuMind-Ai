
from typing import Annotated
import uvicorn
import aiofiles
from fastapi import FastAPI, File, UploadFile
import os
from fastapi.middleware.cors import CORSMiddleware
from routes.summary import summary
from routes.quiz import generate_quiz_cards
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","http://localhost:3001"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def getFileLocation(file: UploadFile = File(...)):
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    file_type=os.path.splitext(file.filename)[1].lower()
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
os.makedirs(UPLOAD_DIR, exist_ok=True)  # Ensure the directory exists

@app.post("/getSummary")
async def GetSummary(file: UploadFile = File(...)):
    path =await getFileLocation(file) 
    file_path=path["file_location"]
    file_type=path["file_type"]
    result =await summary(file_path,file_type) # Make summary async and await
    return {"filename": file.filename, "summary": result, "status": "completed"}



@app.post("/getQuiz")
async def GetQuiz(file: UploadFile = File(...)):
    path =await getFileLocation(file) 
    file_path=path["file_location"]
    file_type=path["file_type"]
    result =await generate_quiz_cards(file_path,file_type) # Make quiz async and await
    return {"filename": file.filename, "summary": result, "status": "completed"}





if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, log_level="info")