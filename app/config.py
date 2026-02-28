from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    APP_NAME: str = 'Medical AI Agent'
    DEBUG: bool = True

    GROQ_API_KEY: str = ''
    GROQ_BASE_URL: str = 'https://api.groq.com/openai/v1'
    PRIMARY_MODEL: str = 'llama-3.3-70b-versatile'
    FALLBACK_MODEL: str = 'llama-3.1-8b-instant'
    FAIL_OPEN: bool = True
    REQUEST_TIMEOUT_S: float = 30.0
    RETRY_COUNT: int = 2
    RETRY_BACKOFF_S: float = 0.5
    TEMPERATURE: float = 0.2
    MAX_TOKENS: int = 512
    TOOL_CHOICE: str = 'auto'

    ENABLE_RAG: bool = True
    ENABLE_TOOLS: bool = True
    ENABLE_GUARDRAILS: bool = True
    MAX_TOOL_ITERATIONS: int = 3

    # ── Open-source model guardrails (run on Groq) ───────────────
    GUARDRAIL_PROMPT_GUARD_MODEL: str = 'meta-llama/llama-prompt-guard-2-86m'
    GUARDRAIL_SAFEGUARD_MODEL: str = 'openai/gpt-oss-safeguard-20b'
    ENABLE_LLM_GUARDRAILS: bool = True          # enable model-based checks alongside regex
    LLM_GUARDRAIL_TIMEOUT_S: float = 10.0       # fast timeout so guardrail doesn't stall chat

    DATABASE_URL: str = 'sqlite:///./medical.db'

    MAX_CONTEXT_MESSAGES: int = 20
    SESSION_TTL_HOURS: int = 24

    MEDICAL_MODE: str = 'info_only'

    RAG_TOP_K: int = 4
    RAG_SCORE_THRESHOLD: float = 0.15
    RAG_DATA_DIR: str = 'app/rag/data'

    REDACT_LOGS: bool = False


settings = Settings()
