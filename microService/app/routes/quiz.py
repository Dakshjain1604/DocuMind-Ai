from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_openai import ChatOpenAI
from app.routes.DocContent import DocContentChunker
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



class QuizQuestion(BaseModel):
    id: int = Field(description="Question ID")
    question: str = Field(description="The quiz question")
    options: List[str] = Field(description="List of 4 multiple choice options")
    correct_answer: str = Field(description="The correct answer from the options")
    explanation: Optional[str] = Field(default="", description="Brief explanation of the correct answer")


class Quiz(BaseModel):
    quiz: List[QuizQuestion] = Field(description="List of quiz questions")

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)  # More consistent output
async def generate_quiz_from_document(path: str, file_type: str) -> Dict[str, Any]:
    try:
        parser = PydanticOutputParser(pydantic_object=Quiz)
        format_instructions = parser.get_format_instructions()
        prompt = create_quiz_prompt().partial(format_instructions=format_instructions)

        db = DocContentChunker(path, file_type)
        if db is None:
            return {"quiz": [], "error": "Could not load or index document."}

        # Better document retrieval
        docs = db.similarity_search(
            "main concepts theories definitions examples key topics", 
            k=3  # Get more content chunks
        )
        
        if not docs:
            return {"quiz": [], "error": "No relevant content found in document."}

        chain = create_stuff_documents_chain(llm, prompt)
        result = await chain.ainvoke({"context": docs})

        # Enhanced parsing with better error handling
        try:
            parsed_result = parser.parse(result)
            return parsed_result.model_dump()
        except Exception as parse_error:
            logger.warning(f"Structured parsing failed: {parse_error}")
            # Try enhanced manual parsing
            return enhanced_manual_parse(result)

    except Exception as e:
        logger.error(f"Quiz generation error: {e}")
        return {"quiz": [], "error": str(e)}

def enhanced_manual_parse(text: str) -> Dict[str, Any]:
    """Better fallback parsing with validation."""
    try:
        # Multiple JSON extraction strategies
        json_patterns = [
            (text.find('{'), text.rfind('}') + 1),
            (text.find('{"quiz"'), text.rfind(']}') + 2),
        ]
        
        for start_idx, end_idx in json_patterns:
            if start_idx != -1 and end_idx > start_idx:
                try:
                    json_str = text[start_idx:end_idx]
                    parsed = json.loads(json_str)
                    
                    if 'quiz' in parsed and isinstance(parsed['quiz'], list):
                        # Validate each question
                        validated_questions = []
                        for q in parsed['quiz']:
                            if validate_question_structure(q):
                                validated_questions.append(q)
                        
                        return {"quiz": validated_questions}
                except json.JSONDecodeError:
                    continue
                    
    except Exception as e:
        logger.warning(f"Enhanced parsing failed: {e}")
    
    return {"quiz": []}

def validate_question_structure(q: Dict) -> bool:
    """Validate individual question structure."""
    required_fields = ['question', 'options', 'correct_answer']
    
    # Check required fields
    if not all(field in q for field in required_fields):
        return False
    
    # Validate options
    options = q.get('options', [])
    if not isinstance(options, list) or len(options) != 4:
        return False
    
    # Check if all options are non-empty strings
    if not all(isinstance(opt, str) and opt.strip() for opt in options):
        return False
    
    # Validate correct answer
    correct_answer = q.get('correct_answer', '').strip()
    if not correct_answer:
        return False
    
    return True

def format_for_frontend(quiz_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert quiz data with enhanced validation and cleaning."""
    cards = []
    
    for i, q in enumerate(quiz_data.get("quiz", [])):
        try:
            # Clean and validate data
            question_text = q.get("question", "").strip()
            if not question_text:
                continue
                
            options = [opt.strip() for opt in q.get("options", [])]
            if len(options) != 4 or not all(options):
                continue
                
            correct_answer = q.get("correct_answer", "").strip()
            
            # Fix common correct_answer matching issues
            if correct_answer not in options:
                # Try to find closest match
                correct_answer = find_closest_match(correct_answer, options)
                if not correct_answer:
                    logger.warning(f"Question {i}: Cannot match correct answer")
                    continue
            
            # Ensure unique ID
            question_id = q.get("id", i + 1)
            
            card = {
                "id": question_id,
                "type": "multiple-choice",
                "title": f"Question {question_id}",
                "question": question_text,
                "options": [
                    {
                        "id": f"option_{j}",
                        "text": option,
                        "correct": option == correct_answer
                    }
                    for j, option in enumerate(options)
                ],
                "correctAnswer": correct_answer,
                "explanation": q.get("explanation", "").strip(),
                "metadata": {
                    "difficulty": determine_difficulty(i, len(quiz_data.get("quiz", []))),
                    "category": "auto-generated"
                }
            }
            cards.append(card)
            
        except Exception as e:
            logger.warning(f"Error formatting question {q.get('id', i)}: {e}")
            continue
    
    return cards

def find_closest_match(target: str, options: List[str]) -> Optional[str]:
    """Find closest matching option for correct answer."""
    target_lower = target.lower().strip()
    
    # Exact match (case insensitive)
    for opt in options:
        if opt.lower().strip() == target_lower:
            return opt
    
    # Partial match
    for opt in options:
        if target_lower in opt.lower() or opt.lower() in target_lower:
            return opt
    
    return None

def determine_difficulty(index: int, total: int) -> str:
    """Determine difficulty based on question position."""
    if index < 4:
        return "easy"
    elif index < total - 4:
        return "medium"
    else:
        return "hard"

def create_quiz_prompt() -> ChatPromptTemplate:
    system_message = """You are an expert professor creating educational quizzes.

**CRITICAL REQUIREMENTS:**
1. Generate exactly 12 multiple choice questions
2. Each question MUST have exactly 4 options labeled A, B, C, D
3. The correct_answer field MUST exactly match one of the 4 options (character-for-character)
4. Questions 1-3: Easy difficulty
5. Questions 4-9: Medium difficulty  
6. Questions 10-12: Hard difficulty
7. Cover different aspects of the document content
8. Provide brief explanations (1-2 sentences)

**STRICT JSON FORMAT:**
{{
  "quiz": [
    {{
      "id": 1,
      "question": "Your question here?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option B",
      "explanation": "Brief explanation here."
    }}
  ]
}}

{format_instructions}

Document Content:
{context}"""
    
    return ChatPromptTemplate.from_messages([("system", system_message)])

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

