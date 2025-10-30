"""
Telegram WebApp authentication utilities.
"""
import hashlib
import hmac
import json
import time
from typing import Optional, Dict, Any
from urllib.parse import unquote, parse_qsl
from pydantic import BaseModel

from app.core.settings import settings


class TelegramWebAppUser(BaseModel):
    """Telegram user from WebApp initData."""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None


def validate_telegram_webapp_data(init_data: str) -> Optional[TelegramWebAppUser]:
    """
    Validate Telegram WebApp initData using HMAC-SHA256.
    
    Args:
        init_data: Raw initData string from Telegram WebApp
        
    Returns:
        TelegramWebAppUser if valid, None if invalid
    """
    try:
        # Parse init_data
        parsed_data = dict(parse_qsl(init_data))
        
        # Extract hash and remove it from data
        received_hash = parsed_data.pop("hash", None)
        if not received_hash:
            return None
        
        # Check auth_date (data should be not older than 24 hours)
        auth_date = parsed_data.get("auth_date")
        if auth_date:
            auth_timestamp = int(auth_date)
            current_timestamp = int(time.time())
            if current_timestamp - auth_timestamp > 86400:  # 24 hours
                return None
        
        # Create data_check_string
        data_check_list = []
        for key in sorted(parsed_data.keys()):
            value = parsed_data[key]
            data_check_list.append(f"{key}={value}")
        data_check_string = "\n".join(data_check_list)
        
        # Generate secret key
        secret_key = hashlib.sha256(settings.telegram_bot_token.encode()).digest()
        
        # Calculate HMAC
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Verify hash
        if not hmac.compare_digest(calculated_hash, received_hash):
            return None
        
        # Parse user data
        user_data = parsed_data.get("user")
        if not user_data:
            return None
        
        user_json = json.loads(unquote(user_data))
        return TelegramWebAppUser(**user_json)
        
    except Exception:
        return None


def validate_dev_mode(init_data: str) -> Optional[TelegramWebAppUser]:
    """
    Development mode: extract user without validation.
    Only use in development environment!
    """
    try:
        parsed_data = dict(parse_qsl(init_data))
        
        # Check if dev mode
        if parsed_data.get("dev_mode") != "true":
            return None
            
        user_data = parsed_data.get("user")
        if not user_data:
            return None
        
        user_json = json.loads(unquote(user_data))
        return TelegramWebAppUser(**user_json)
    except Exception:
        return None
