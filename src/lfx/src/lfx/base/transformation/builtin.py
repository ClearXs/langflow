"""Built-in transformation functions."""

import hashlib
import re
from datetime import datetime
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
        """Remove leading and trailing whitespace (清除两端空格)."""
        return str(value).strip() if value is not None else value

    @staticmethod
    def trim_all(value: Any) -> Any:
        """Remove all whitespace characters (清除空格符)."""
        if value is None:
            return value
        return re.sub(r"\s+", "", str(value))

    @staticmethod
    def to_number(value: Any) -> float | int | None:
        """Convert string to number (字符串转为数字)."""
        if value is None:
            return None
        try:
            s = str(value).strip()
            # Try int first
            if "." not in s:
                return int(s)
            # Then float
            return float(s)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def substring_after(value: Any, separator: str = ",") -> str:
        """Extract substring after separator (截取符号之后字符)."""
        if value is None:
            return ""
        s = str(value)
        if separator in s:
            return s.split(separator, 1)[1]
        return s

    @staticmethod
    def substring_before(value: Any, separator: str = ",") -> str:
        """Extract substring before separator (截取符号之前字符)."""
        if value is None:
            return ""
        s = str(value)
        if separator in s:
            return s.split(separator, 1)[0]
        return s

    @staticmethod
    def replace_string(value: Any, old: str = "", new: str = "") -> str:
        """Replace string (替换字符串)."""
        if value is None:
            return ""
        return str(value).replace(old, new)

    @staticmethod
    def substring(value: Any, start: int = 0, length: int | None = None) -> str:
        """Extract substring (字符串截取)."""
        if value is None:
            return ""
        s = str(value)
        if length is None:
            return s[start:]
        return s[start : start + length]

    @staticmethod
    def timestamp_to_string(value: Any, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Convert timestamp integer to string (时间整数转为字符串)."""
        if value is None:
            return ""
        try:
            timestamp = int(value)
            # Handle both seconds and milliseconds timestamps
            if timestamp > 10**10:
                timestamp = timestamp / 1000
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime(format_str)
        except (ValueError, TypeError, OSError):
            return str(value)

    @staticmethod
    def date_format(value: Any, input_format: str = "%Y-%m-%d", output_format: str = "%Y/%m/%d") -> str:
        """Format date string (日期格式化)."""
        if value is None:
            return ""
        try:
            s = str(value).strip()
            # Try parsing with input format
            dt = datetime.strptime(s, input_format)
            return dt.strftime(output_format)
        except (ValueError, TypeError):
            # If parsing fails, return original
            return str(value)

    @staticmethod
    def amount_to_chinese(value: Any) -> str:
        """Convert amount to Chinese uppercase (金额转大写)."""
        if value is None:
            return ""

        try:
            amount = float(value)
            if amount < 0:
                return f"负{BuiltInTransformations.amount_to_chinese(-amount)}"

            # Chinese number characters
            cn_nums = ["零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖"]
            cn_units = ["", "拾", "佰", "仟"]
            cn_big_units = ["", "万", "亿", "兆"]

            # Split integer and decimal parts
            amount_str = f"{amount:.2f}"
            integer_part, decimal_part = amount_str.split(".")

            # Convert integer part
            integer_cn = ""
            integer_len = len(integer_part)

            for i, digit in enumerate(integer_part):
                digit_int = int(digit)
                position = integer_len - i - 1

                if digit_int != 0:
                    integer_cn += cn_nums[digit_int] + cn_units[position % 4]
                elif integer_cn and integer_cn[-1] != "零":
                    integer_cn += "零"

                # Add big units (万, 亿)
                if position % 4 == 0 and position > 0:
                    integer_cn += cn_big_units[position // 4]

            integer_cn = integer_cn.rstrip("零") + "元"

            # Convert decimal part
            decimal_cn = ""
            if int(decimal_part[0]) > 0:
                decimal_cn += cn_nums[int(decimal_part[0])] + "角"
            if int(decimal_part[1]) > 0:
                decimal_cn += cn_nums[int(decimal_part[1])] + "分"

            if not decimal_cn:
                decimal_cn = "整"

            return integer_cn + decimal_cn

        except (ValueError, TypeError):
            return str(value)

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
