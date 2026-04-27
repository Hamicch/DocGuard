from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Try root .env first (monorepo layout), fall back to local .env for
    # environments where the working directory is already backend/.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    database_url: str = ""

    github_app_id: str = ""
    github_app_private_key: str = ""
    github_webhook_secret: str = ""

    # Webhook dispatch strategy:
    # - background: local dev only (FastAPI BackgroundTasks)
    # - lambda_async: async invoke a worker Lambda
    # - sqs: enqueue an audit task to SQS
    audit_dispatch_mode: str = "background"
    audit_worker_lambda_name: str = ""
    audit_sqs_queue_url: str = ""

    # Provider-agnostic LLM client settings.
    # Default base URL points at OpenRouter (OpenAI-compatible).
    # Override LLM_BASE_URL + LLM_API_KEY to switch providers without code changes.
    llm_api_key: str = ""
    llm_base_url: str = "https://openrouter.ai/api/v1"

    aws_region: str = "us-east-1"


settings = Settings()
