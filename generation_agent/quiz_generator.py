import os
import json
import logging
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from .data_models import AssessmentQuiz, MCQQuestion
from .api_tracker import APITracker
from langchain.callbacks.base import BaseCallbackHandler

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Prompt template for generating MCQs
assessment_quiz_template = """
As an AI assessment expert, create a comprehensive quiz for {subject}.

SPECIFIC INSTRUCTIONS:
1. Generate {num_easy} easy, {num_medium} medium, and {num_hard} hard multiple-choice questions
2. Create scenario-based questions that test application, not memorization
3. Ensure questions reflect current industry practices and tools for {subject}
4. For each question:
   - Provide exactly 4 options with only one correct answer
   - Write plausible distractors that represent common misconceptions
   - Include a detailed explanation for why the correct answer is right and others are wrong
   - Mark the difficulty level as "easy", "medium", or "hard"

Remember: Questions should test practical knowledge professionals need, not theoretical concepts.

{format_instructions}
"""

def _clean_json_output(json_str: any) -> str:
    """
    Clean and format JSON string output from LLM.
    
    Args:
        json_str: The JSON string (or object with content) to clean
        
    Returns:
        str: Cleaned JSON string that matches expected schema
    """
    if json_str is None:
        logger.warning("Received None response from LLM")
        return "{}"
        
    if not isinstance(json_str, str):
        if hasattr(json_str, "content"):
            json_str = json_str.content
        else:
            json_str = str(json_str)
    
    # Remove any code fences if present
    if json_str.startswith("```json"):
        json_str = json_str.replace("```json", "", 1)
        fence_end = json_str.rfind("```")
        if fence_end != -1:
            json_str = json_str[:fence_end]
    elif json_str.startswith("```"):
        json_str = json_str.replace("```", "", 1)
        fence_end = json_str.rfind("```")
        if fence_end != -1:
            json_str = json_str[:fence_end]
                
    json_str = json_str.strip()
    
    # Balance braces and brackets
    open_braces = json_str.count('{')
    close_braces = json_str.count('}')
    open_brackets = json_str.count('[')
    close_brackets = json_str.count(']')
    
    if open_braces > close_braces:
        json_str += "}" * (open_braces - close_braces)
    if open_brackets > close_brackets:
        json_str += "]" * (open_brackets - close_brackets)
    
    if json_str.startswith('{') and json_str.endswith('}]'):
        json_str = json_str[:-1]

    # Attempt to parse the JSON string and extract items if needed
    try:
        data = json.loads(json_str)
        if isinstance(data, dict) and "items" in data:
            data = data["items"]
        return json.dumps(data)
    except Exception as e:
        logger.error(f"Failed to parse JSON: {e}")
        return json_str

def initialize_llm():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite",
        google_api_key=api_key,
        temperature=0.7
        # callbacks parameter omitted
    )

class QuizGenerator:
    """Class to generate assessment quizzes using LLM or dummy data."""
    def __init__(self):
        try:
            self.llm = initialize_llm()
            self.quiz_parser = PydanticOutputParser(pydantic_object=AssessmentQuiz)
            self.prompt = ChatPromptTemplate.from_template(
                template=assessment_quiz_template,
                partial_variables={"format_instructions": self.quiz_parser.get_format_instructions()}
            )
            self.chain = self.prompt | self.llm
            self.use_llm = True
        except Exception as e:
            print(f"Failed to initialize LLM: {e}")
            self.use_llm = False

    def generate_assessment_quiz(self, subject, num_easy, num_medium, num_hard):
        """Generate a quiz with specified number of questions per difficulty."""
        if self.use_llm:
            try:
                response = self.chain.invoke({
                    "subject": subject,
                    "num_easy": num_easy,
                    "num_medium": num_medium,
                    "num_hard": num_hard
                })
                # Clean the JSON output before parsing
                cleaned_output = _clean_json_output(response.content)
                quiz = self.quiz_parser.parse(cleaned_output)
                return [q.dict() for q in quiz.root]
            except Exception as e:
                print(f"Error generating quiz: {e}")
        # Fallback to dummy questions
        return generate_dummy_assessment_quiz(subject, num_easy, num_medium, num_hard)

def generate_dummy_assessment_quiz(subject, num_easy=5, num_medium=5, num_hard=5):
    """Generate dummy questions as a fallback."""
    questions = []
    for i in range(num_easy):
        questions.append({
            "question": f"Easy Question {i+1} about {subject}?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_option": 0,
            "explanation": f"Explanation for Easy Question {i+1}",
            "difficulty": "easy"
        })
    for i in range(num_medium):
        questions.append({
            "question": f"Medium Question {i+1} about {subject}?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_option": 1,
            "explanation": f"Explanation for Medium Question {i+1}",
            "difficulty": "medium"
        })
    for i in range(num_hard):
        questions.append({
            "question": f"Hard Question {i+1} about {subject}?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_option": 2,
            "explanation": f"Explanation for Hard Question {i+1}",
            "difficulty": "hard"
        })
    return questions
