from pydantic import BaseModel, Field
from typing import List, Dict, Any
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate
from routes.DocContent import DocContent
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_openai import ChatOpenAI
import logging

# Configure logging
logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    model="gpt-4-turbo",  # More powerful model for complex tasks
    temperature=0.1,  # Lower temperature for more factual accuracy
    max_tokens=4096
)

class QuizQuestion(BaseModel):
    question: str = Field(description="Clear and unambiguous question")
    options: List[str] = Field(description="Exactly 4 distinct multiple choice options", min_items=4, max_items=4)
    correct_answer: str = Field(description="The single correct answer option")
    explanation: str = Field(description="Brief explanation of why the answer is correct")

class QuizResponse(BaseModel):
    quiz: List[QuizQuestion] = Field(description="List of 5 quiz questions", min_items=5, max_items=5)
    document_overview: str = Field(description="Brief 2-sentence summary of the source document")

async def generate_quiz(path: str, file_type: str) -> dict:
    """Generate structured quiz from document content"""
    parser = PydanticOutputParser(pydantic_object=QuizResponse)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""
You are an expert educational content creator. Generate high-quality quiz questions based on the document.

**Task Requirements:**
1. Create exactly 5 MCQs covering key concepts
2. For each question:
   - Phrase questions clearly and unambiguously
   - Provide 4 distinct options (A-D)
   - Mark the single correct answer
   - Add 1-sentence explanation
3. Include a 2-sentence document overview
4. Ensure:
   - Questions test conceptual understanding
   - Options are plausible but contain only one correct answer
   - Avoid trivial or opinion-based questions

**Output Format:**
{parser.get_format_instructions()}

Document:
{{context}}""")
    ])
    
    try:
        # Process document
        doc = DocContent(path, file_type)
        docs = [doc]
        
        # Generate quiz
        chain = create_stuff_documents_chain(llm, prompt)
        result = await chain.ainvoke({"context": docs})
        
        # Parse and validate
        parsed = parser.parse(result)
        return parsed.dict()
    
    except Exception as e:
        logger.error(f"Quiz generation failed: {str(e)}")
        return {
            "error": "Quiz generation failed. Please try again or use a different document.",
            "details": str(e)
        }

# This is the function you should import
async def generate_quiz_cards(path: str, file_type: str) -> dict:
    """Main function to generate quiz cards for frontend"""
    try:
        quiz_data = await generate_quiz(path, file_type)
        
        # Transform to frontend format
        if "error" in quiz_data:
            return quiz_data
            
        return {
            "document_overview": quiz_data.get("document_overview", ""),
            "questions": [
                {
                    "id": idx + 1,
                    "question": q["question"],
                    "options": [
                        {"id": f"opt-{idx}-{opt_idx}", "text": opt}
                        for opt_idx, opt in enumerate(q["options"])
                    ],
                    "correct_answer": q["correct_answer"],
                    "explanation": q["explanation"]
                }
                for idx, q in enumerate(quiz_data["quiz"])
            ]
        }
        
    except Exception as e:
        logger.error(f"Quiz card generation failed: {str(e)}")
        return {
            "error": "Failed to process quiz. Please try again.",
            "details": str(e)
        }