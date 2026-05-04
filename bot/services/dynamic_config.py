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

    def get_user_vouchers(self, user_id: int) -> list:
        """Get the full list of vouchers for a user."""
        user_id_str = str(user_id)
        vouchers = self.data.get("user_vouchers", {}).get(user_id_str, [])
        # Handle backward compatibility (if it was a string)
        if isinstance(vouchers, str):
            return [vouchers] if vouchers else []
        return vouchers

    def get_active_user_voucher(self, user_id: int) -> str | None:
        """Get the current active (first) voucher for a user."""
        vouchers = self.get_user_vouchers(user_id)
        return vouchers[0] if vouchers else None

    def add_user_voucher(self, user_id: int, value: str):
        """Add a new voucher to the user's pool (accumulation)."""
        user_id_str = str(user_id)
        if "user_vouchers" not in self.data:
            self.data["user_vouchers"] = {}
        
        current_vouchers = self.get_user_vouchers(user_id)
        
        # Prevent duplicates
        if value not in current_vouchers:
            current_vouchers.append(value)
            self.data["user_vouchers"][user_id_str] = current_vouchers
            self.save()

    def remove_first_user_voucher(self, user_id: int):
        """Remove the current voucher (usually because it's empty)."""
        user_id_str = str(user_id)
        vouchers = self.get_user_vouchers(user_id)
        if vouchers:
            vouchers.pop(0)
            self.data["user_vouchers"][user_id_str] = vouchers
            self.save()

    def clear_user_vouchers(self, user_id: int):
        """Clear all vouchers for a user."""
        user_id_str = str(user_id)
        if user_id_str in self.data.get("user_vouchers", {}):
            self.data["user_vouchers"][user_id_str] = []
            self.save()
