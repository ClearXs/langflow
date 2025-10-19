"""Built-in transformation functions."""

import hashlib
import re
from typing import Any


class BuiltInTransformations:
    """Collection of built-in transformation functions."""

    @staticmethod
    def upper(value: Any) -> Any:
        """Convert to uppercase."""
        return str(value).upper() if value is not None else value

    @staticmethod
    def lower(value: Any) -> Any:
        """Convert to lowercase."""
        return str(value).lower() if value is not None else value

    @staticmethod
    def trim(value: Any) -> Any:
        """Remove leading and trailing whitespace."""
        return str(value).strip() if value is not None else value

    @staticmethod
    def mask_phone(value: Any) -> Any:
        """Mask phone number (e.g., 138****1234)."""
        if value is None:
            return value
        s = str(value)
        # Remove non-digit characters
        digits = re.sub(r"\D", "", s)
        if len(digits) >= 11:
            return f"{digits[:3]}****{digits[-4:]}"
        if len(digits) >= 7:
            return f"{digits[:3]}****{digits[-2:]}"
        return value

    @staticmethod
    def mask_idcard(value: Any) -> Any:
        """Mask ID card number."""
        if value is None:
            return value
        s = str(value)
        if len(s) >= 18:
            return f"{s[:6]}********{s[-4:]}"
        if len(s) >= 15:
            return f"{s[:6]}*****{s[-4:]}"
        return value

    @staticmethod
    def mask_email(value: Any) -> Any:
        """Mask email address."""
        if value is None:
            return value
        s = str(value)
        if "@" in s:
            local, domain = s.split("@", 1)
            if len(local) > 2:
                masked_local = f"{local[0]}***{local[-1]}"
            else:
                masked_local = f"{local[0]}***"
            return f"{masked_local}@{domain}"
        return value

    @staticmethod
    def mask_name(value: Any) -> Any:
        """Mask name (keep first and last char)."""
        if value is None:
            return value
        s = str(value)
        if len(s) <= 1:
            return s
        if len(s) == 2:
            return f"{s[0]}*"
        return f"{s[0]}{'*' * (len(s) - 2)}{s[-1]}"

    @staticmethod
    def md5(value: Any) -> str:
        """Generate MD5 hash."""
        if value is None:
            return ""
        return hashlib.md5(str(value).encode()).hexdigest()

    @staticmethod
    def sha256(value: Any) -> str:
        """Generate SHA256 hash."""
        if value is None:
            return ""
        return hashlib.sha256(str(value).encode()).hexdigest()

    @staticmethod
    def to_int(value: Any) -> int | None:
        """Convert to integer."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def to_float(value: Any) -> float | None:
        """Convert to float."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def to_str(value: Any) -> str:
        """Convert to string."""
        return str(value) if value is not None else ""

    @staticmethod
    def to_bool(value: Any) -> bool:
        """Convert to boolean."""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        s = str(value).lower()
        return s in ("true", "yes", "1", "on", "enabled")
