# security/validators.py
# Production input validation.
# Every piece of user input — query params, request bodies, NL questions —
# goes through these validators before touching the database or AI layer.

import re
from typing import Optional, Literal
from pydantic import BaseModel, field_validator, model_validator, Field


# ── CONSTANTS ──────────────────────────────────────────────────────────────────
MAX_QUESTION_LENGTH   = 500    # NL query max characters
MIN_QUESTION_LENGTH   = 5      # Reject single-character queries
MAX_USER_ID_LENGTH    = 128
VALID_YEAR_RANGE      = range(2004, 2026)   # NSSO rounds start 2004
VALID_STATE_CODES     = set(range(1, 36))   # 1-35 (includes UTs)
VALID_SECTOR_CODES    = {1, 2}              # 1=Rural, 2=Urban
VALID_SEX_CODES       = {1, 2}             # 1=Male, 2=Female
VALID_LANGUAGES       = {"en", "hi", "ta", "te", "bn", "kn", "mr", "gu", "pa", "ml"}

# Characters allowed in user IDs (alphanumeric, @, ., _, -)
USER_ID_REGEX   = re.compile(r"^[a-zA-Z0-9@._\-]{3,128}$")

# Prompt injection patterns — reject NL questions containing these
_INJECTION_PATTERNS = re.compile(
    r"(ignore.{0,20}(previous|above|prior)|"
    r"forget.{0,20}instruction|"
    r"you are now|"
    r"act as|"
    r"system prompt|"
    r"jailbreak|"
    r"DAN mode|"
    r"<\|im_start\|>|"     # ChatML injection
    r"\[INST\])",           # Llama injection
    re.IGNORECASE
)


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class TokenRequest(BaseModel):
    user_id:  str  = Field(..., min_length=3, max_length=128)
    password: str  = Field(..., min_length=12, max_length=128)
    scope:    Literal["public", "research", "admin"] = "public"

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        v = v.strip()   # strip whitespace before validation
        if not USER_ID_REGEX.match(v):
            raise ValueError(
                "user_id must be 3-128 characters: letters, numbers, @, ., _, -"
            )
        return v.lower()

    @field_validator("password")
    @classmethod
    def no_null_bytes(cls, v: str) -> str:
        if "\x00" in v:
            raise ValueError("Password contains invalid characters")
        return v


class RefreshRequest(BaseModel):
    # Refresh token comes from HttpOnly cookie — no body needed
    # This model is a placeholder for future explicit refresh flows
    pass


class IndicatorQueryParams(BaseModel):
    """Validated query parameters for all indicator endpoints."""
    year:    int  = Field(2023, ge=2004, le=2025)
    state:   Optional[int] = Field(None, ge=1, le=35)
    sector:  Optional[int] = Field(None, ge=1, le=2)
    sex:     Optional[int] = Field(None, ge=1, le=2)

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: int) -> int:
        if v not in VALID_YEAR_RANGE:
            raise ValueError(f"Year must be between {min(VALID_YEAR_RANGE)} and {max(VALID_YEAR_RANGE)}")
        return v

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in VALID_STATE_CODES:
            raise ValueError(f"State code {v} is not valid. Must be 1-35.")
        return v


class NLQueryRequest(BaseModel):
    """Validated natural language query body."""
    question: str = Field(
        ...,
        min_length=MIN_QUESTION_LENGTH,
        max_length=MAX_QUESTION_LENGTH,
        description="Plain English question about the survey data",
    )
    language: str = Field(
        "en",
        description=f"ISO 639-1 language code. Supported: {sorted(VALID_LANGUAGES)}"
    )

    @field_validator("question")
    @classmethod
    def sanitize_question(cls, v: str) -> str:
        v = v.strip()

        # Reject empty after stripping
        if not v:
            raise ValueError("Question cannot be empty")

        # Reject prompt injection attempts
        if _INJECTION_PATTERNS.search(v):
            raise ValueError(
                "Question contains disallowed patterns. "
                "Please ask a genuine survey data question."
            )

        # Reject questions that look like raw SQL
        sql_keywords = re.compile(
            r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|FROM|WHERE)\b",
            re.IGNORECASE
        )
        sql_hits = sql_keywords.findall(v)
        if len(sql_hits) >= 2:
            raise ValueError(
                "Question appears to contain SQL. "
                "Please ask in plain language."
            )

        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in VALID_LANGUAGES:
            raise ValueError(
                f"Language '{v}' not supported. "
                f"Supported: {sorted(VALID_LANGUAGES)}"
            )
        return v


class APIKeyCreateRequest(BaseModel):
    user_id:     str = Field(..., min_length=3, max_length=128)
    scope:       Literal["public", "research"] = "public"  # admin keys issued manually
    description: str = Field(..., min_length=5, max_length=256)

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        if not USER_ID_REGEX.match(v):
            raise ValueError("Invalid user_id format")
        return v.lower().strip()

    @field_validator("description")
    @classmethod
    def sanitize_description(cls, v: str) -> str:
        # Strip any HTML/script tags from the description
        v = re.sub(r"<[^>]+>", "", v).strip()
        return v
