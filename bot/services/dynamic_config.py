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
                    data = json.load(f)
                    if "user_vouchers" not in data:
                        data["user_vouchers"] = {}
                    return data
            except Exception as e:
                logger.error(f"Error loading dynamic config: {e}")
        return {"voucher": "", "user_vouchers": {}}

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

    def get_user_voucher(self, user_id: int) -> str | None:
        """Get voucher for a specific user ID."""
        user_id_str = str(user_id)
        return self.data.get("user_vouchers", {}).get(user_id_str)

    def set_user_voucher(self, user_id: int, value: str):
        """Set voucher for a specific user ID."""
        if "user_vouchers" not in self.data:
            self.data["user_vouchers"] = {}
        self.data["user_vouchers"][str(user_id)] = value
        self.save()
