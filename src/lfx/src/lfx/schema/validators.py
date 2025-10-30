from datetime import datetime, timezone

import i18n
from pydantic import BeforeValidator


def timestamp_to_str(timestamp: datetime | str | float) -> str:
    """Convert timestamp to standardized string format.

    Handles multiple input formats and ensures consistent UTC timezone output.

    Args:
        timestamp (datetime | str | float | int): Input timestamp either as datetime object, string, or numeric timestamp

    Returns:
        str: Formatted timestamp string in 'YYYY-MM-DD HH:MM:SS UTC' format

    Raises:
        ValueError: If string timestamp is in invalid format
    """
    # Handle numeric timestamps (Unix timestamp)
    if isinstance(timestamp, (float, int)):
        try:
            timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (ValueError, OSError) as e:
            msg = i18n.t("schema.validators.errors.invalid_numeric_timestamp", timestamp=timestamp)
            raise ValueError(msg) from e

    if isinstance(timestamp, str):
        # Try parsing with different formats
        formats = [
            "%Y-%m-%dT%H:%M:%S",  # ISO format
            "%Y-%m-%d %H:%M:%S %Z",  # Standard with timezone
            "%Y-%m-%d %H:%M:%S",  # Without timezone
            "%Y-%m-%dT%H:%M:%S.%f",  # ISO with microseconds
            "%Y-%m-%dT%H:%M:%S%z",  # ISO with numeric timezone
        ]

        for fmt in formats:
            try:
                parsed = datetime.strptime(timestamp.strip(), fmt).replace(tzinfo=timezone.utc)
                return parsed.strftime("%Y-%m-%d %H:%M:%S %Z")
            except ValueError:
                continue

        msg = i18n.t("schema.validators.errors.invalid_timestamp_format", timestamp=timestamp)
        raise ValueError(msg)

    # Handle datetime object
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")


def str_to_timestamp(timestamp: str | datetime | float) -> datetime:
    """Convert timestamp to datetime object.

    Handles multiple input formats and ensures consistent UTC timezone output.

    Args:
        timestamp (str | datetime | float | int): Input timestamp either as string, datetime object, or numeric timestamp

    Returns:
        datetime: Datetime object with UTC timezone

    Raises:
        ValueError: If string timestamp is not in 'YYYY-MM-DD HH:MM:SS UTC' format
    """
    # Handle numeric timestamps (Unix timestamp)
    if isinstance(timestamp, (float, int)):
        try:
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (ValueError, OSError) as e:
            msg = i18n.t("schema.validators.errors.invalid_numeric_timestamp", timestamp=timestamp)
            raise ValueError(msg) from e

    if isinstance(timestamp, str):
        try:
            return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S %Z").replace(tzinfo=timezone.utc)
        except ValueError as e:
            msg = i18n.t("schema.validators.errors.invalid_timestamp_format_expected", timestamp=timestamp)
            raise ValueError(msg) from e
    return timestamp


def timestamp_with_fractional_seconds(timestamp: datetime | str | float) -> str:
    """Convert timestamp to string format including fractional seconds.

    Handles multiple input formats and ensures consistent UTC timezone output.

    Args:
        timestamp (datetime | str | float | int): Input timestamp either as datetime object, string, or numeric timestamp

    Returns:
        str: Formatted timestamp string in 'YYYY-MM-DD HH:MM:SS.ffffff UTC' format

    Raises:
        ValueError: If string timestamp is in invalid format
    """
    # Handle numeric timestamps (Unix timestamp)
    if isinstance(timestamp, (float, int)):
        try:
            timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (ValueError, OSError) as e:
            msg = i18n.t("schema.validators.errors.invalid_numeric_timestamp", timestamp=timestamp)
            raise ValueError(msg) from e

    if isinstance(timestamp, str):
        # Try parsing with different formats
        formats = [
            "%Y-%m-%d %H:%M:%S.%f %Z",  # Standard with timezone
            "%Y-%m-%d %H:%M:%S.%f",  # Without timezone
            "%Y-%m-%dT%H:%M:%S.%f",  # ISO format
            "%Y-%m-%dT%H:%M:%S.%f%z",  # ISO with numeric timezone
            # Also try without fractional seconds
            "%Y-%m-%d %H:%M:%S %Z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
        ]

        for fmt in formats:
            try:
                parsed = datetime.strptime(timestamp.strip(), fmt).replace(tzinfo=timezone.utc)
                return parsed.strftime("%Y-%m-%d %H:%M:%S.%f %Z")
            except ValueError:
                continue

        msg = i18n.t("schema.validators.errors.invalid_timestamp_format", timestamp=timestamp)
        raise ValueError(msg)

    # Handle datetime object
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.strftime("%Y-%m-%d %H:%M:%S.%f %Z")


timestamp_to_str_validator = BeforeValidator(timestamp_to_str)
timestamp_with_fractional_seconds_validator = BeforeValidator(timestamp_with_fractional_seconds)
str_to_timestamp_validator = BeforeValidator(str_to_timestamp)
