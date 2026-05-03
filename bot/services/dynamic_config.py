import json
import os
import logging

logger = logging.getLogger(__name__)

class DynamicConfig:
    """Manages configuration that changes at runtime and needs persistence."""
    
    def __init__(self, file_path: str = "bot/data/dynamic_config.json"):
        self.file_path = file_path
        self._ensure_dir()
        self.data = self._load()

    def _ensure_dir(self):
        directory = os.path.dirname(self.file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

    def _load(self) -> dict:
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading dynamic config: {e}")
        return {"voucher": ""}

    def save(self):
        try:
            with open(self.file_path, 'w') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving dynamic config: {e}")

    def get_voucher(self) -> str:
        return self.data.get("voucher", "")

    def set_voucher(self, value: str):
        self.data["voucher"] = value
        self.save()
