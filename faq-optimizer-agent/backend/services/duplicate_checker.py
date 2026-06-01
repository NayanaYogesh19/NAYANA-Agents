from backend.database.faq_repository import FAQRepository

from typing import List, Dict

import logging
import re

from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class DuplicateChecker:
    """
    Advanced semantic duplicate checker
    """

    def __init__(self):

        self.repo = FAQRepository()

        # LOWER threshold catches more duplicates
        self.similarity_threshold = 0.65

    # =================================================
    # FILTER DUPLICATES
    # =================================================

    def filter_duplicates(
        self,
        questions: List[Dict],
        company_name: str
    ) -> List[Dict]:

        try:

            logger.info(
                f"Checking duplicates for: {company_name}"
            )

            existing_faqs = (
                self.repo.get_faqs_by_company(
                    company_name
                )
            )

            existing_questions = []

            # -----------------------------------------
            # EXISTING QUESTIONS
            # -----------------------------------------

            if existing_faqs:

                existing_questions = [

                    self.normalize_question(
                        faq.get("question", "")
                    )

                    for faq in existing_faqs
                ]

            unique_questions = []

            current_session_questions = []

            duplicates_removed = 0

            # -----------------------------------------
            # CHECK NEW QUESTIONS
            # -----------------------------------------

            for q in questions:

                original_question = (
                    q["question"]
                )

                normalized = (
                    self.normalize_question(
                        original_question
                    )
                )

                is_duplicate = False

                # =====================================
                # CHECK DATABASE QUESTIONS
                # =====================================

                for existing in existing_questions:

                    similarity = (
                        SequenceMatcher(
                            None,
                            normalized,
                            existing
                        ).ratio()
                    )

                    if similarity >= self.similarity_threshold:

                        logger.info(
                            f"DUPLICATE FOUND: "
                            f"{original_question}"
                        )

                        is_duplicate = True

                        duplicates_removed += 1

                        break

                # =====================================
                # CHECK CURRENT SESSION QUESTIONS
                # =====================================

                if not is_duplicate:

                    for current in current_session_questions:

                        similarity = (
                            SequenceMatcher(
                                None,
                                normalized,
                                current
                            ).ratio()
                        )

                        if similarity >= self.similarity_threshold:

                            logger.info(
                                f"SESSION DUPLICATE: "
                                f"{original_question}"
                            )

                            is_duplicate = True

                            duplicates_removed += 1

                            break

                # =====================================
                # UNIQUE QUESTION
                # =====================================

                if not is_duplicate:

                    unique_questions.append(q)

                    current_session_questions.append(
                        normalized
                    )

            logger.info(
                f"Removed {duplicates_removed} duplicates"
            )

            logger.info(
                f"Remaining unique questions: "
                f"{len(unique_questions)}"
            )

            return unique_questions

        except Exception as e:

            logger.error(
                f"Duplicate check error: {e}"
            )

            return questions

    # =================================================
    # NORMALIZE QUESTION
    # =================================================

    def normalize_question(
        self,
        question: str
    ) -> str:

        question = question.lower()

        # REMOVE SYMBOLS
        question = re.sub(
            r'[^a-zA-Z0-9\s]',
            '',
            question
        )

        # REMOVE EXTRA SPACES
        question = re.sub(
            r'\s+',
            ' ',
            question
        ).strip()

        # =============================================
        # SEMANTIC NORMALIZATION
        # =============================================

        replacements = {

            "placement services":
                "placements",

            "placement support":
                "placements",

            "job placements":
                "placements",

            "career opportunities":
                "placements",

            "employability":
                "placements",

            "training programs":
                "training",

            "workshops":
                "training",

            "industry partners":
                "industry",

            "industry collaboration":
                "industry",

            "students":
                "student"
        }

        for old, new in replacements.items():

            question = question.replace(
                old,
                new
            )

        return question

    # =================================================
    # OPTIONAL ANSWER DUPLICATE CHECK
    # =================================================

    def is_duplicate_answer(
        self,
        answer: str,
        existing_answers: List[str]
    ) -> bool:

        normalized = (
            self.normalize_question(answer)
        )

        for existing in existing_answers:

            similarity = (
                SequenceMatcher(
                    None,
                    normalized,
                    self.normalize_question(existing)
                ).ratio()
            )

            if similarity >= 0.70:

                return True

        return False