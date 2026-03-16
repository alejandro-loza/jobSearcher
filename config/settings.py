from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # OpenAI / Anthropic (fallback)
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")

    # GLM-4.7 (ZhipuAI) - LLM legacy
    glm_api_key: str = Field(default="", env="GLM_API_KEY")
    glm_model: str = Field(default="glm-4-plus", env="GLM_MODEL")
    glm_base_url: str = Field(
        default="https://open.bigmodel.cn/api/paas/v4/", env="GLM_BASE_URL"
    )
    glm_temperature: float = Field(default=0.7, env="GLM_TEMPERATURE")
    glm_max_tokens: int = Field(default=4096, env="GLM_MAX_TOKENS")

    # Groq - LLM principal
    groq_api_key: str = Field(default="", env="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", env="GROQ_MODEL")
    groq_vision_model: str = Field(default="meta-llama/llama-4-scout-17b-16e-instruct", env="GROQ_VISION_MODEL")

    # SambaNova - LLM alternativo
    sambanova_api_key: str = Field(default="", env="SAMBANOVA_API_KEY")
    sambanova_model: str = Field(default="Meta-Llama-3.3-70B-Instruct", env="SAMBANOVA_MODEL")

    # WhatsApp
    whatsapp_bridge_url: str = Field(
        default="http://localhost:3001", env="WHATSAPP_BRIDGE_URL"
    )
    whatsapp_my_number: str = Field(default="", env="WHATSAPP_MY_NUMBER")

    # Gmail
    gmail_credentials_file: str = Field(
        default="config/google_credentials.json", env="GMAIL_CREDENTIALS_FILE"
    )
    gmail_token_file: str = Field(
        default="config/gmail_token.json", env="GMAIL_TOKEN_FILE"
    )
    gmail_my_email: str = Field(default="", env="GMAIL_MY_EMAIL")

    # Google Calendar
    calendar_credentials_file: str = Field(
        default="config/google_credentials.json", env="CALENDAR_CREDENTIALS_FILE"
    )
    calendar_token_file: str = Field(
        default="config/calendar_token.json", env="CALENDAR_TOKEN_FILE"
    )
    calendar_id: str = Field(default="primary", env="CALENDAR_ID")

    # LinkedIn
    linkedin_cookies_file: str = Field(default="config/linkedin_cookies.json", env="LINKEDIN_COOKIES_FILE")
    linkedin_profile_file: str = Field(default="config/linkedin_profile.json", env="LINKEDIN_PROFILE_FILE")
    linkedin_profile_url: str = Field(default="", env="LINKEDIN_PROFILE_URL")
    linkedin_email: str = Field(default="", env="LINKEDIN_EMAIL")
    linkedin_password: str = Field(default="", env="LINKEDIN_PASSWORD")

    # Job Search
    job_search_interval_hours: int = Field(default=6, env="JOB_SEARCH_INTERVAL_HOURS")
    email_check_interval_minutes: int = Field(
        default=30, env="EMAIL_CHECK_INTERVAL_MINUTES"
    )
    job_match_threshold: int = Field(default=75, env="JOB_MATCH_THRESHOLD")
    followup_days: int = Field(default=7, env="FOLLOWUP_DAYS")
    resume_file: str = Field(default="data/resume.json", env="RESUME_FILE")

    # CrewAI
    crewai_process_type: str = Field(default="hierarchical", env="CREWAI_PROCESS_TYPE")
    crewai_memory_enabled: bool = Field(default=True, env="CREWAI_MEMORY_ENABLED")
    crewai_cache_enabled: bool = Field(default=True, env="CREWAI_CACHE_ENABLED")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_dir: str = Field(default="logs", env="LOG_DIR")

    # Database
    db_path: str = Field(default="data/jobsearcher.db", env="DB_PATH")

    # Orchestrator
    orchestrator_host: str = Field(default="0.0.0.0", env="ORCHESTRATOR_HOST")
    orchestrator_port: int = Field(default=8000, env="ORCHESTRATOR_PORT")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


# Global settings instance
settings = Settings()
