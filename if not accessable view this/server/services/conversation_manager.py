import json
import os
import logging

logger = logging.getLogger("ConversationManager")

class ConversationManager:
    """
    Manages interactive WhatsApp workflow sessions.
    Stores session state in-memory and persists to a JSON file to survive Uvicorn reloads.
    """
    _sessions = {}
    _file_path = "sessions.json"

    @classmethod
    def load(cls):
        """Load sessions from disk if available."""
        if os.path.exists(cls._file_path):
            try:
                with open(cls._file_path, "r", encoding="utf-8") as f:
                    cls._sessions = json.load(f)
                logger.info(f"Loaded {len(cls._sessions)} sessions from {cls._file_path}")
            except Exception as e:
                logger.error(f"Failed to load sessions: {e}")

    @classmethod
    def save(cls):
        """Persist sessions to disk."""
        try:
            with open(cls._file_path, "w", encoding="utf-8") as f:
                json.dump(cls._sessions, f)
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")

    @classmethod
    def save_session(cls, phone_number: str, session_data: dict):
        """Save a user's workflow session state."""
        cls._sessions[phone_number] = session_data
        logger.info(f"💾 Saved session for {phone_number}")
        cls.save()

    @classmethod
    def get_session(cls, phone_number: str) -> dict:
        """Retrieve a user's workflow session state."""
        if not cls._sessions and os.path.exists(cls._file_path):
            cls.load()
        return cls._sessions.get(phone_number)

    @classmethod
    def clear_session(cls, phone_number: str):
        """Clear a user's workflow session state."""
        if phone_number in cls._sessions:
            del cls._sessions[phone_number]
            logger.info(f"🗑️ Cleared session for {phone_number}")
            cls.save()

# Attempt initial load
ConversationManager.load()
