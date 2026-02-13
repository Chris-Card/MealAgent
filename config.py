"""Configuration management for the weekly dinner planning agent."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Central configuration class for the meal planning agent."""
    
    # Email configuration
    GMAIL_SMTP_HOST: str = "smtp.gmail.com"
    GMAIL_SMTP_PORT: int = 587
    GMAIL_USERNAME: str = os.getenv("GMAIL_USERNAME", "")
    GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "")
    TARGET_EMAIL: str = os.getenv("TARGET_EMAIL", "")
    
    # Servings configuration
    ADULT_SERVINGS: int = int(os.getenv("ADULT_SERVINGS", "2"))
    CHILD_SERVINGS: int = int(os.getenv("CHILD_SERVINGS", "2"))
    LEFTOVERS_FACTOR: float = float(os.getenv("LEFTOVERS_FACTOR", "1.3"))  # 30% extra for leftovers
    
    # LLM configuration (Claude / Anthropic)
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "claude-3-5-haiku-latest")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4000"))
    
    # Behavior configuration
    RUN_DAY: str = os.getenv("RUN_DAY", "MONDAY")
    TIMEZONE: str = os.getenv("TIMEZONE", "America/New_York")
    INCLUDE_HTML_EMAIL: bool = os.getenv("INCLUDE_HTML_EMAIL", "true").lower() == "true"
    
    @classmethod
    def validate(cls) -> list[str]:
        """Validate that required configuration values are set."""
        errors = []
        if not cls.GMAIL_USERNAME:
            errors.append("GMAIL_USERNAME is required")
        if not cls.GMAIL_APP_PASSWORD:
            errors.append("GMAIL_APP_PASSWORD is required")
        if not cls.TARGET_EMAIL:
            errors.append("TARGET_EMAIL is required")
        if not cls.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY is required")
        return errors
