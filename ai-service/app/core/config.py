import os
from dotenv import load_dotenv

# Load local environment file if exists
load_dotenv()

class Settings:
    PORT: int = int(os.getenv("PORT", "8000"))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    INTERNAL_API_SECRET: str = os.getenv("INTERNAL_API_SECRET", "finance_controller_internal_secret_key_2026")
    
    # PostgreSQL Configuration (finance_ai_user)
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5434"))
    DB_NAME: str = os.getenv("DB_NAME", "finance_controller")
    DB_USER: str = os.getenv("DB_USER", "finance_ai_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "ai_secure_password")
    
    # Google Gemini Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")

    # Redis Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6380"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "redis_secure_password")

    # RabbitMQ Configuration
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://finance_admin:rabbitmq_secure_password@localhost:5672")

settings = Settings()
