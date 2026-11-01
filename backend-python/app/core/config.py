import json
import os
import secrets
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Synaptic Chat"
    PORT: int = int(os.getenv("PORT", "3011"))
    ENVIRONMENT: str = os.getenv("NODE_ENV", "production")
    
    # Database & Redis
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:synapticchat@forgecrm-db:5432/postgres")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379")
    
    # Storage & Persistence
    DATA_DIR: str = os.getenv("SYNAPTICCHAT_DATA_DIR") or os.getenv("FORGECHAT_DATA_DIR") or "/app/data"
    MEDIA_DIR: str = os.getenv("MEDIA_DIR", "/app/media")
    UPLOADS_DIR: str = os.getenv("UPLOADS_DIR", "/app/uploads")
    
    # Super Admin Configuration
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "vtdhilipkumar@gmail.com").strip().lower()
    ADMIN_PASSWORD: Optional[str] = os.getenv("ADMIN_PASSWORD")
    
    # Secrets (Loaded dynamically from instance.json or environment)
    JWT_SECRET: str = ""
    ENCRYPTION_KEY: str = ""
    
    # Cookie Configuration
    COOKIE_NAME: str = "synapticchat_token"
    LEGACY_COOKIE_NAME: str = "forgecrm_token"
    TOKEN_EXPIRE_HOURS: int = 24
    
    # Meta WhatsApp
    META_APP_SECRET: Optional[str] = os.getenv("META_APP_SECRET")
    META_API_VERSION: str = os.getenv("META_API_VERSION", "v21.0")

    def bootstrap_secrets(self):
        """Loads or generates persistent JWT_SECRET and ENCRYPTION_KEY matching Node instanceSecrets.js."""
        data_path = Path(self.DATA_DIR)
        data_path.mkdir(parents=True, exist_ok=True, mode=0o700)
        instance_file = data_path / "instance.json"
        
        file_data = {}
        if instance_file.exists():
            try:
                with open(instance_file, "r", encoding="utf-8") as f:
                    file_data = json.load(f)
            except Exception as e:
                print(f"[config] Warning reading instance.json: {e}")
                
        # Resolve JWT Secret
        env_jwt = os.getenv("JWT_SECRET")
        if env_jwt and len(env_jwt) >= 32 and env_jwt not in ("synapticchat-dev-secret-change-me", "forgecrm-dev-secret-change-me"):
            self.JWT_SECRET = env_jwt
        elif file_data.get("jwtSecret"):
            self.JWT_SECRET = file_data["jwtSecret"]
        else:
            self.JWT_SECRET = secrets.token_hex(32)
            file_data["jwtSecret"] = self.JWT_SECRET

        # Resolve Encryption Key
        env_enc = os.getenv("SYNAPTICCHAT_ENCRYPTION_KEY") or os.getenv("FORGECRM_ENCRYPTION_KEY")
        if env_enc and len(env_enc) >= 32:
            self.ENCRYPTION_KEY = env_enc
        elif file_data.get("encryptionKey"):
            self.ENCRYPTION_KEY = file_data["encryptionKey"]
        else:
            self.ENCRYPTION_KEY = secrets.token_hex(32)
            file_data["encryptionKey"] = self.ENCRYPTION_KEY

        # Persist if needed
        if "jwtSecret" not in file_data or "encryptionKey" not in file_data or not instance_file.exists():
            file_data["version"] = 1
            if "generatedAt" not in file_data:
                from datetime import datetime, timezone
                file_data["generatedAt"] = datetime.now(timezone.utc).isoformat()
            tmp_file = str(instance_file) + ".tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(file_data, f, indent=2)
            os.replace(tmp_file, instance_file)
            print(f"[config] Persisted instance secrets to {instance_file}")

settings = Settings()
settings.bootstrap_secrets()
