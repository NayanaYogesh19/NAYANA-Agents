from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum

# =====================================================
# FAQ CATEGORY
# =====================================================

class FAQCategory(str, Enum):

    AEO = "AEO"

    GEO = "GEO"

    SEO = "SEO"

# =====================================================
# QUESTION GENERATION REQUEST
# =====================================================

class QuestionGenerationRequest(BaseModel):

    website_url: str

    topic: str

# =====================================================
# QUESTION MODEL
# =====================================================

class Question(BaseModel):

    question: str

    category: str

# =====================================================
# QUESTION GENERATION RESPONSE
# =====================================================

class QuestionGenerationResponse(BaseModel):

    questions: List[Question]

    total_count: int

    message: str = (
        "Questions generated successfully"
    )

# =====================================================
# SELECTED QUESTION MODEL
# =====================================================

class SelectedQuestion(BaseModel):

    question: str

    # ==============================================
    # FIXED CATEGORY TYPE
    # ==============================================

    category: str

# =====================================================
# ANSWER GENERATION REQUEST
# =====================================================

class AnswerGenerationRequest(BaseModel):

    website_url: str

    topic: str

    selected_questions: List[SelectedQuestion]

# =====================================================
# FAQ MODEL
# =====================================================

class FAQ(BaseModel):

    question: str

    answer: str

    # ==============================================
    # FIXED CATEGORY TYPE
    # ==============================================

    category: str

    # ---------------------------------------------
    # PERFORMANCE METRICS
    # ---------------------------------------------

    performance_score: int = 0

    predicted_impressions: int = 0

    predicted_clicks: int = 0

    predicted_ctr: float = 0.0

# =====================================================
# ANALYTICS MODEL
# =====================================================

class Analytics(BaseModel):

    total_faqs: int = 0

    total_impressions: int = 0

    total_clicks: int = 0

    average_ctr: float = 0.0

    seo_questions: int = 0

    geo_questions: int = 0

    aeo_questions: int = 0

# =====================================================
# ANSWER GENERATION RESPONSE
# =====================================================

class AnswerGenerationResponse(BaseModel):

    faqs: List[FAQ]

    company_name: str

    topic: str

    analytics: Optional[Dict[str, Any]] = None

    message: str = (
        "Answers generated successfully"
    )

# =====================================================
# ERROR RESPONSE
# =====================================================

class ErrorResponse(BaseModel):

    error: str

    detail: Optional[str] = None