CREDENTIAL_TYPE = "Credential"
GENERIC_TYPE = "Generic"
SYSTEM_TYPE = "system"

# System variables definitions
SYSTEM_VARIABLES = {
    "currentDateTime": {
        "name": "currentDateTime",
        "display_name": "当前时间",
        "display_name_en": "Current DateTime",
        "description": "系统当前时间 yyyy-MM-dd HH:mm:SS",
        "example": "2025-11-20 10:30:45",
    },
    "currentDate": {
        "name": "currentDate",
        "display_name": "当前日期",
        "display_name_en": "Current Date",
        "description": "系统当前日期 yyyy-MM-dd",
        "example": "2025-11-20",
    },
    "uniqueId24": {
        "name": "uniqueId24",
        "display_name": "唯一ID(24位)",
        "display_name_en": "Unique ID (24 chars)",
        "description": "生成24位唯一字符串",
        "example": "674e6b71cafee70164ce507a",
    },
    "uuid32": {
        "name": "uuid32",
        "display_name": "UUID(32位)",
        "display_name_en": "UUID (32 chars)",
        "description": "生成32位UUID字符串",
        "example": "4336da8258444391a7673312d55fcda9",
    },
    "lastStartTime": {
        "name": "lastStartTime",
        "display_name": "上次开始时间",
        "display_name_en": "Last Start Time",
        "description": "获取上一次流程开始运行的时间",
        "example": "2025-11-20 09:15:30",
    },
    "lastEndTime": {
        "name": "lastEndTime",
        "display_name": "上次结束时间",
        "display_name_en": "Last End Time",
        "description": "获取上一次流程结束运行的时间",
        "example": "2025-11-20 09:16:45",
    },
    "lastSuccessStartTime": {
        "name": "lastSuccessStartTime",
        "display_name": "上次成功开始时间",
        "display_name_en": "Last Success Start Time",
        "description": "获取上一次流程成功开始运行的时间",
        "example": "2025-11-20 09:15:30",
    },
    "lastSuccessEndTime": {
        "name": "lastSuccessEndTime",
        "display_name": "上次成功结束时间",
        "display_name_en": "Last Success End Time",
        "description": "获取上一次流程成功结束运行的时间",
        "example": "2025-11-20 09:16:45",
    },
}


def is_system_variable(name: str) -> bool:
    """Check if a variable name is a system variable.

    Args:
        name: Variable name to check

    Returns:
        True if the name matches a system variable, False otherwise
    """
    return name in SYSTEM_VARIABLES


def get_system_variable_info(name: str) -> dict | None:
    """Get system variable information by name.

    Args:
        name: System variable name

    Returns:
        Dictionary with variable info or None if not found
    """
    return SYSTEM_VARIABLES.get(name)
