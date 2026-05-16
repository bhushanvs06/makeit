import json
import os
import logging

logger = logging.getLogger("SettingsManager")

class SettingsManager:
    _file_path = "settings.json"
    _settings = {
        "whatsapp_listener_enabled": False
    }

    @classmethod
    def load(cls):
        if os.path.exists(cls._file_path):
            try:
                with open(cls._file_path, "r", encoding="utf-8") as f:
                    cls._settings.update(json.load(f))
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")

    @classmethod
    def save(cls):
        try:
            with open(cls._file_path, "w", encoding="utf-8") as f:
                json.dump(cls._settings, f)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    @classmethod
    def get(cls, key: str, default=None):
        return cls._settings.get(key, default)

    @classmethod
    def set(cls, key: str, value):
        cls._settings[key] = value
        cls.save()

# Load on startup
SettingsManager.load()
