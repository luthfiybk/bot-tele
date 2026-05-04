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
        """Get the full list of voucher objects [{"key": "...", "balance": 0}] for a user."""
        user_id_str = str(user_id)
        vouchers = self.data.get("user_vouchers", {}).get(user_id_str, [])
        
        # Backward compatibility: Convert list of strings to list of dicts
        if isinstance(vouchers, list) and len(vouchers) > 0 and isinstance(vouchers[0], str):
            new_vouchers = [{"key": v, "balance": 0} for v in vouchers]
            self.data["user_vouchers"][user_id_str] = new_vouchers
            self.save()
            return new_vouchers
        # Handle single string
        if isinstance(vouchers, str):
            new_vouchers = [{"key": vouchers, "balance": 0}] if vouchers else []
            self.data["user_vouchers"][user_id_str] = new_vouchers
            self.save()
            return new_vouchers
            
        return vouchers

    def get_active_user_voucher(self, user_id: int) -> str | None:
        """Get the current active (first) voucher key for a user."""
        vouchers = self.get_user_vouchers(user_id)
        return vouchers[0]["key"] if vouchers else None

    def add_user_voucher(self, user_id: int, value: str):
        """Add a new voucher to the user's pool."""
        user_id_str = str(user_id)
        if "user_vouchers" not in self.data:
            self.data["user_vouchers"] = {}
        
        current_vouchers = self.get_user_vouchers(user_id)
        
        # Prevent duplicates
        if not any(v["key"] == value for v in current_vouchers):
            current_vouchers.append({"key": value, "balance": 0})
            self.data["user_vouchers"][user_id_str] = current_vouchers
            self.save()

    def update_voucher_balance(self, user_id: int, key: str, balance: int):
        """Update the last known balance for a specific voucher."""
        user_id_str = str(user_id)
        vouchers = self.get_user_vouchers(user_id)
        changed = False
        for v in vouchers:
            if v["key"] == key:
                v["balance"] = balance
                changed = True
                break
        if changed:
            self.data["user_vouchers"][user_id_str] = vouchers
            self.save()

    def get_total_balance(self, user_id: int) -> int:
        """Calculate the total known balance from all vouchers."""
        vouchers = self.get_user_vouchers(user_id)
        return sum(v.get("balance", 0) for v in vouchers)

    def remove_first_user_voucher(self, user_id: int):
        """Remove the current voucher."""
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
