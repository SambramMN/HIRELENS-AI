import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "hirelens-ai-secure-secret-key-2026")
    
    # Check if running in a serverless environment like Vercel
    IS_SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
    
    # Database path
    DEFAULT_DB_DIR = Path("/tmp") if IS_SERVERLESS else BASE_DIR / "instance"
    DEFAULT_DB_PATH = DEFAULT_DB_DIR / "hirelens.db"
    
    DATABASE_PATH = os.environ.get("DATABASE_PATH")
    if not DATABASE_PATH:
        DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
        DATABASE_PATH = str(DEFAULT_DB_PATH)
    else:
        Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
        
    # Uploads path
    DEFAULT_UPLOAD_DIR = Path("/tmp/uploads") if IS_SERVERLESS else BASE_DIR / "uploads"
    DEFAULT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_FOLDER = str(DEFAULT_UPLOAD_DIR)
    
    MAX_CONTENT_LENGTH = int(os.environ.get("UPLOAD_MAX_FILE_SIZE_MB", 16)) * 1024 * 1024
    ALLOWED_EXTENSIONS = {"pdf", "txt"}
    
    # LLM settings
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
    OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()
    LLM_TIMEOUT_SECONDS = int(os.environ.get("LLM_TIMEOUT_SECONDS", 30))
    
    # Blind screening default
    BLIND_SCREENING_DEFAULT = os.environ.get("BLIND_SCREENING_DEFAULT", "false").lower() in ("true", "1", "yes")
    
    # Auto reload templates
    TEMPLATES_AUTO_RELOAD = True

config = Config()
