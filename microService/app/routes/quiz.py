from pydantic import BaseModel, Field
from typing import List, Dict, Any
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate
from routes.DocContent import DocContent
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini",temperature=0.2)
class QuizQuestion(BaseModel):
    id: int = Field(description="Question ID")
    question: str = Field(description="The quiz question")
    options: List[str] = Field(description="List of 4 multiple choice options")
    correct_answer: str = Field(description="The correct answer from the options")
    explanation: str = Field(description="Brief explanation of the correct answer")

class Quiz(BaseModel):
    quiz: List[QuizQuestion] = Field(description="List of quiz questions")

async def Quiz(path, file_type):
    """Generate a quiz from file content using structured output"""
    
    # Set up the parser
    parser = PydanticOutputParser(pydantic_object=Quiz)
    
    prompt_Quiz = ChatPromptTemplate.from_messages(
        [("system", """You are an expert professor skilled at simplifying complex information and creating clear, well-structured summaries. 

        **Task:**  
        Generate 5 MCQ questions from the context, give 4 options for each question and an answer for it.

        1. **difficulty**: keep it relevant to the type of document.  

        **Formatting Guidelines**:  
        - Use clear headings and understandable questions that give clear understanding and overall topic coverage.  
        - Avoid similar questions and open ended questions.  
        - Ensure logical flow between topics.  

        {format_instructions}

        Document:  
        {context}""")]
    )
    
    # Add format instructions to the prompt
    formatted_prompt = prompt_Quiz.partial(format_instructions=parser.get_format_instructions())
    
    doc = DocContent(path, file_type)
    docs = [doc]
    
    chain = create_stuff_documents_chain(llm, formatted_prompt)
    result = await chain.ainvoke({"context": docs})
    
    # Parse the result
    try:
        parsed_result = parser.parse(result)
        return parsed_result.dict()
    except Exception as e:
        print(f"Parsing error: {e}")
        # Fallback to manual parsing
        return e

# def manual_parse_fallback(text: str) -> Dict[str, Any]:
#     """Manual parsing as fallback"""
#     # Implementation similar to parse_text_to_json from previous example
#     pass

# Frontend card formatter
def to_card_format(quiz_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert quiz data to frontend card format"""
    return [
        {
            "id": q["id"],
            "type": "multiple-choice",
            "title": f"Question {q['id']}",
            "question": q["question"],
            "options": [
                {"id": f"option_{i}", "text": option, "correct": option == q["correct_answer"]}
                for i, option in enumerate(q["options"])
            ],
            "correctAnswer": q["correct_answer"],
            "explanation": q.get("explanation", ""),
            "metadata": {
                "difficulty": "medium",
                "category": "auto-generated"
            }
        }
        for q in quiz_data.get("quiz", [])
    ]

# Complete usage
async def generate_quiz_cards(path, file_type):
    """Main function to generate quiz cards for frontend"""
    try:
        quiz_data = await Quiz(path, file_type)
        cards = to_card_format(quiz_data)
        
        return {
            "success": True,
            "data": {
                "total_questions": len(cards),
                "cards": cards
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {"total_questions": 0, "cards": []}
        }