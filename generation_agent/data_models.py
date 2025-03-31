from pydantic import BaseModel, Field, field_validator, RootModel
from typing import List, Dict, Optional, Union


class MCQQuestion(BaseModel):
    question: str = Field(description="The question text")
    options: List[str] = Field(description="Multiple choice options (4 options)")
    correct_option: int = Field(description="Index of the correct option (0-3)")
    explanation: str = Field(description="Explanation for the correct answer")
    difficulty: str = Field(description="Difficulty level: easy, medium, or hard")
    
    def dict(self, *args, **kwargs):
        # Custom dict method to handle serialization
        return {
            "question": self.question,
            "options": self.options,
            "correct_option": self.correct_option,
            "explanation": self.explanation,
            "difficulty": self.difficulty
        }
    
class AssessmentQuiz(RootModel):
    root: List[MCQQuestion]