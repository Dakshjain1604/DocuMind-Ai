from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_openai import ChatOpenAI
from routes.DocContent import DocContent
import json
import logging

# Configure logging for debugging and monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the language model (LLM) for quiz generation
llm = ChatOpenAI(model="gpt-4o-mini", temperature=1)

# -----------------------------
# Data Models for Quiz Structure
# -----------------------------

# Model for a single quiz question
class QuizQuestion(BaseModel):
    id: int = Field(description="Question ID")
    question: str = Field(description="The quiz question")
    options: List[str] = Field(description="List of 4 multiple choice options")
    correct_answer: str = Field(description="The correct answer from the options")
    explanation: Optional[str] = Field(default="", description="Brief explanation of the correct answer")

# Model for the overall quiz (list of questions)
class Quiz(BaseModel):
    quiz: List[QuizQuestion] = Field(description="List of quiz questions")

# -----------------------------------
# Prompt Template for Quiz Generation
# -----------------------------------
def create_quiz_prompt() -> ChatPromptTemplate:
    """Create the quiz generation prompt template for the LLM."""
    system_message = """You are an expert professor creating educational quizzes.

**Task:** Generate 15 to 20 multiple choice questions from the provided document content in which the questions are related to the content of the document and the difficulty leveel for foist 3-4 is easy then medium then hard , include 
    questions related to theory and content of the document , avoid asking questions that dont hold relevence to the content

**Requirements:**
- Each question must have exactly 4 options
- Only one correct answer per question
- Questions should cover different topics from the document
- Avoid repetitive or overly similar questions
- Use clear, concise language
- Provide brief explanations for correct answers

**Format:** Return a JSON object with a 'quiz' key containing a list of questions.
Each question should have: id, question, options, correct_answer, explanation.

{format_instructions}

Document Content:
{context}"""
    
    return ChatPromptTemplate.from_messages([("system", system_message)])

# -----------------------------------
# Fallback Manual Parsing for LLM Output
# -----------------------------------
def manual_parse_quiz(text: str) -> Dict[str, Any]:
    """Fallback manual parsing when structured output fails (tries to extract JSON from text)."""
    try:
        # Try to extract JSON from the text
        start_idx = text.find('{')
        end_idx = text.rfind('}') + 1
        
        if start_idx != -1 and end_idx != -1:
            json_str = text[start_idx:end_idx]
            parsed = json.loads(json_str)
            
            # Validate structure
            if 'quiz' in parsed and isinstance(parsed['quiz'], list):
                return parsed
                
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Manual parsing failed: {e}")
    
    # Return empty structure if parsing fails
    return {"quiz": []}

# ---------------------------------------------------
# Generate Quiz Questions from Document (Async LLM)
# ---------------------------------------------------
async def generate_quiz_from_document(path: str, file_type: str) -> Dict[str, Any]:
    """Generate quiz questions from document content using LLM."""
    
    # Set up parser and prompt
    parser = PydanticOutputParser(pydantic_object=Quiz)
    prompt = create_quiz_prompt()
    
    try:
        # Get format instructions for the LLM output
        format_instructions = parser.get_format_instructions()
        formatted_prompt = prompt.partial(format_instructions=format_instructions)
        
        # Load document content
        doc = DocContent(path, file_type)
        docs = [doc]
        
        # Create and run the LLM chain
        chain = create_stuff_documents_chain(llm, formatted_prompt)
        result = await chain.ainvoke({"context": docs})
        
        # Try to parse the result using the structured parser
        try:
            parsed_result = parser.parse(result)
            return parsed_result.dict()
        except Exception as parse_error:
            logger.warning(f"Structured parsing failed: {parse_error}")
            # Fall back to manual parsing if structured parsing fails
            return manual_parse_quiz(result)
            
    except Exception as e:
        logger.error(f"Quiz generation error: {e}")
        return {"quiz": []}

# ---------------------------------------------------
# Format Quiz Data for Frontend Consumption
# ---------------------------------------------------
def format_for_frontend(quiz_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert quiz data to frontend-compatible format (cards with options and metadata)."""
    cards = []
    
    for q in quiz_data.get("quiz", []):
        try:
            # Ensure correct_answer is in options
            correct_answer = q.get("correct_answer", "")
            options = q.get("options", [])
            
            if correct_answer not in options:
                logger.warning(f"Question {q.get('id')}: correct_answer not in options")
                continue
            
            # Build the card structure expected by the frontend
            card = {
                "id": q.get("id"),
                "type": "multiple-choice",
                "title": f"Question {q.get('id')}",
                "question": q.get("question", ""),
                "options": [
                    {
                        "id": f"option_{i}",
                        "text": option,
                        "correct": option == correct_answer
                    }
                    for i, option in enumerate(options)
                ],
                "correctAnswer": correct_answer,
                "explanation": q.get("explanation", ""),
                "metadata": {
                    "difficulty": "medium",
                    "category": "auto-generated"
                }
            }
            cards.append(card)
            
        except Exception as e:
            logger.warning(f"Error formatting question {q.get('id', 'unknown')}: {e}")
            continue
    
    return cards

# ---------------------------------------------------
# Main Function to Generate Quiz Cards for Frontend
# ---------------------------------------------------
async def generate_quiz_cards(path: str, file_type: str) -> Dict[str, Any]:
    """Main function to generate quiz cards for frontend consumption."""
    try:
        # Generate quiz data from document
        quiz_data = await generate_quiz_from_document(path, file_type)
        
        # Format for frontend
        cards = format_for_frontend(quiz_data)
        
        # Validate we have questions
        if not cards:
            return {
                "success": False,
                "error": "No valid quiz questions could be generated",
                "data": {"total_questions": 0, "cards": []}
            }
        
        return {
            "success": True,
            "data": {
                "total_questions": len(cards),
                "cards": cards
            }
        }
        
    except Exception as e:
        logger.error(f"Quiz card generation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {"total_questions": 0, "cards": []}
        }

# -------------------
# Usage Example (CLI)
# -------------------
if __name__ == "__main__":
    import asyncio
    
    async def test_quiz_generation():
        result = await generate_quiz_cards("sample.pdf", "pdf")
        print(f"Generated {result['data']['total_questions']} questions")
        
    # asyncio.run(test_quiz_generation())