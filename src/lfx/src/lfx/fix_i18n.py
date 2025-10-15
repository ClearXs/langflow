#!/usr/bin/env python3
"""
Script to fix i18n files for ETL components.
Extracts all i18n.t() calls from component files and ensures both EN and ZH files have all required keys.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, Set, List, Tuple


def extract_i18n_keys(file_path: Path) -> Set[str]:
    """Extract all i18n.t() keys from a Python file."""
    content = file_path.read_text(encoding='utf-8')

    # Pattern to match i18n.t('key') or i18n.t("key") or i18n.t('key', args)
    pattern = r"i18n\.t\(['\"]([^'\"]+)['\"](?:,\s*[^)]+)?\)"

    matches = re.findall(pattern, content)
    return set(matches)


def parse_key_path(key: str) -> List[str]:
    """Parse a dotted key path into a list of parts."""
    return key.split('.')


def create_nested_dict(key_path: List[str], value: str) -> Dict:
    """Create a nested dictionary from a key path."""
    if len(key_path) == 1:
        return {key_path[0]: value}

    return {key_path[0]: create_nested_dict(key_path[1:], value)}


def merge_dicts(base: Dict, update: Dict) -> Dict:
    """Recursively merge two dictionaries."""
    result = base.copy()

    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value

    return result


def get_nested_value(d: Dict, key_path: List[str]) -> str | None:
    """Get a value from a nested dictionary using a key path."""
    current = d
    for part in key_path:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current if isinstance(current, str) else None


def set_nested_value(d: Dict, key_path: List[str], value: str):
    """Set a value in a nested dictionary using a key path."""
    current = d
    for i, part in enumerate(key_path[:-1]):
        if part not in current:
            current[part] = {}
        elif not isinstance(current[part], dict):
            # Convert to dict if it's not already
            current[part] = {}
        current = current[part]
    current[key_path[-1]] = value


def generate_english_text(key_parts: List[str]) -> str:
    """Generate reasonable English text from a key path."""
    last_part = key_parts[-1]

    # Convert snake_case to Title Case
    words = last_part.replace('_', ' ').split()
    title = ' '.join(word.capitalize() for word in words)

    # Handle special cases
    if last_part == 'display_name':
        return title
    elif last_part == 'info':
        parent = key_parts[-2] if len(key_parts) > 1 else ''
        return f"Information about {parent.replace('_', ' ')}"
    elif last_part == 'description':
        return "Component description"
    elif 'error' in last_part or last_part in ['file_not_found', 'read_failed', 'invalid_json', 'unsupported_type']:
        return f"Error: {title}"
    elif last_part in ['reading', 'success', 'processing']:
        return f"{title}..."
    else:
        return title


def generate_chinese_translation(english: str, key_parts: List[str]) -> str:
    """Generate Chinese translation from English text and key context."""
    last_part = key_parts[-1]

    # Common translations
    translations = {
        # Display names - General
        'Display Name': '显示名称',
        'Data': '数据',
        'Data Input': '数据输入',
        'File Info': '文件信息',
        'File Path': '文件路径',
        'File Type': '文件类型',
        'Encoding': '编码',
        'Delimiter': '分隔符',
        'Has Header': '包含标题行',
        'Skip Rows': '跳过行数',
        'Max Rows': '最大行数',
        'Sheet Name': '工作表名称',
        'Include Header': '包含标题',
        'Include Index': '包含索引',

        # Components
        'File Input': '文件输入',
        'File Output': '文件输出',
        'Table Input': '表格输入',
        'Table Output': '表格输出',
        'API Input': 'API输入',
        'API Output': 'API输出',
        'CDC Input': 'CDC输入',
        'Kafka Input': 'Kafka输入',
        'CSV Output': 'CSV输出',
        'Excel Output': 'Excel输出',

        # API related
        'API URL': 'API地址',
        'API Key Header': 'API密钥请求头',
        'API Key Value': 'API密钥值',
        'HTTP Method': 'HTTP方法',
        'Custom Headers': '自定义请求头',
        'Request Body': '请求体',
        'Timeout (seconds)': '超时时间(秒)',
        'Timeout (Seconds)': '超时时间(秒)',
        'Retry Count': '重试次数',
        'Authentication Type': '认证类型',
        'Bearer Token': 'Bearer令牌',
        'Username': '用户名',
        'Password': '密码',
        'Data Path': '数据路径',
        'Batch Size': '批次大小',
        'Send as Batch': '批量发送',
        'Send As Batch': '批量发送',

        # CDC related
        'CDC Mode': 'CDC模式',
        'Table Name': '表名',
        'Timestamp Column': '时间戳列',
        'Primary Keys': '主键',
        'Last Sync Time': '最后同步时间',
        'Poll Interval (seconds)': '轮询间隔(秒)',
        'Poll Interval (Seconds)': '轮询间隔(秒)',
        'Capture Deletes': '捕获删除',
        'Include Change Type': '包含变更类型',

        # Kafka related
        'Kafka Servers': 'Kafka服务器',
        'Topic': '主题',
        'Consumer Group': '消费者组',
        'Auto Offset Reset': '自动偏移重置',
        'Enable Auto Commit': '启用自动提交',

        # Operations
        'Deduplication': '去重',
        'Dual Stream Join': '双流合并',
        'Group By': '分组',
        'Multi Stream Union': '多流合并',
        'Join Type': '连接类型',
        'Join Key': '连接键',
        'Group Keys': '分组键',
        'Aggregation Functions': '聚合函数',

        # Manipulations
        'Data Cleaning': '数据清洗',
        'Field Name Mapping': '字段名映射',
        'Field Split': '字段拆分',
        'Field Value Mapping': '字段值映射',
        'Field Value Merge': '字段值合并',
        'Mapping Rules': '映射规则',
        'Split Delimiter': '拆分分隔符',
        'Target Fields': '目标字段',

        # Security
        'Data Encryption': '数据加密',
        'Data Masking': '数据脱敏',
        'Encryption Key': '加密密钥',
        'Masking Rules': '脱敏规则',
        'Masking Pattern': '脱敏模式',

        # Scripts
        'Python Script': 'Python脚本',
        'Shell Script': 'Shell脚本',
        'Script Code': '脚本代码',
        'Script Path': '脚本路径',

        # Status messages
        'Reading...': '读取中...',
        'Processing...': '处理中...',
        'Success...': '成功...',
        'Writing...': '写入中...',
        'Sending...': '发送中...',
        'Fetching...': '获取中...',

        # Common info messages
        'Information about file path': '文件路径信息',
        'Information about encoding': '编码信息',
        'Information about delimiter': '分隔符信息',
        'REST API endpoint': 'REST API端点',
        'Records per batch': '每批记录数',
        'Data to send': '要发送的数据',
        'Data to export': '要导出的数据',
        'No data to send': '没有要发送的数据',
        'No data to export': '没有要导出的数据',
        'HTTP headers': 'HTTP请求头',
        'HTTP request method': 'HTTP请求方法',
        'Request timeout': '请求超时',
        'Request timeout in seconds': '请求超时时间(秒)',
        'Send records in batches': '批量发送记录',
        'Header name for API key': 'API密钥的请求头名称',
        'API key value': 'API密钥值',
        'Basic auth username': '基本认证用户名',
        'Basic auth password': '基本认证密码',
        'Type of authentication to use': '使用的认证类型',
        'Bearer token for authentication': '用于认证的Bearer令牌',
        'JSONPath to extract data from response': '从响应中提取数据的JSONPath',
        'Additional HTTP headers': '额外的HTTP请求头',
        'JSON request body for POST': 'POST请求的JSON请求体',
        'Number of retry attempts': '重试次数',
        'Output CSV file path': '输出CSV文件路径',
        'Output Excel file path': '输出Excel文件路径',
        'Include column headers': '包含列标题',
        'Include row index': '包含行索引',
        'Field delimiter': '字段分隔符',
        'File encoding': '文件编码',
        'Excel sheet name': 'Excel工作表名称',
        'Change capture mode': '变更捕获模式',
        'Table to monitor for changes': '监控变更的表',
        'Column to track changes': '跟踪变更的列',
        'Primary key columns (comma-separated)': '主键列(逗号分隔)',
        'Last synchronization timestamp': '最后同步时间戳',
        'Polling interval in seconds': '轮询间隔(秒)',
        'Include deleted records': '包含已删除记录',
        'Add change type metadata': '添加变更类型元数据',
        'Number of changes per batch': '每批变更数',

        # Error messages
        'Error: File Not Found': '错误: 文件未找到',
        'Error: Read Failed': '错误: 读取失败',
        'Error: Invalid Json': '错误: 无效的JSON',
        'Error: Unsupported Type': '错误: 不支持的类型',
        'Error: No Data': '错误: 没有数据',
        'Error: Audit Table Missing': '错误: 审计表缺失',
        'Error: Invalid Mode': '错误: 无效的模式',
    }

    # Check for direct translation
    if english in translations:
        return translations[english]

    # Pattern-based translations
    if english.startswith('Information about '):
        field = english.replace('Information about ', '')
        field_zh = translations.get(field.title(), field)
        return f"{field_zh}的信息"

    if english.startswith('Error: '):
        error_text = english.replace('Error: ', '')
        error_zh = translations.get(error_text, error_text)
        return f"错误: {error_zh}"

    # For description fields, provide generic but useful text
    if last_part == 'description':
        parent = key_parts[-2] if len(key_parts) > 1 else ''
        parent_zh = translations.get(parent.replace('_', ' ').title(), parent.replace('_', ' '))
        return f"{parent_zh}组件"

    # Return the English as fallback (will be obvious what needs translation)
    return english


def fix_i18n_files(component_path: Path, en_i18n_path: Path, zh_i18n_path: Path, dry_run: bool = False):
    """Fix i18n files for a single component."""
    # Extract keys from component
    keys = extract_i18n_keys(component_path)

    if not keys:
        print(f"  No i18n keys found in {component_path.name}")
        return

    print(f"\n  Found {len(keys)} keys in {component_path.name}")

    # Load existing i18n files
    en_data = json.loads(en_i18n_path.read_text(encoding='utf-8')) if en_i18n_path.exists() else {}
    zh_data = json.loads(zh_i18n_path.read_text(encoding='utf-8')) if zh_i18n_path.exists() else {}

    # Track changes
    en_missing = []
    zh_missing = []

    # Check and add missing keys
    for full_key in sorted(keys):
        # Extract the component-specific part of the key
        # Keys are like: components.input_output.file_input.display_name
        parts = parse_key_path(full_key)

        # Skip the "components.category.component_name" prefix
        if len(parts) >= 4 and parts[0] == 'components':
            key_parts = parts[3:]  # Get parts after component name
        else:
            key_parts = parts

        # Check EN
        en_value = get_nested_value(en_data, key_parts)
        if en_value is None:
            en_text = generate_english_text(key_parts)
            set_nested_value(en_data, key_parts, en_text)
            en_missing.append('.'.join(key_parts))
            print(f"    [EN] Added: {'.'.join(key_parts)} = {en_text}")

        # Check ZH
        zh_value = get_nested_value(zh_data, key_parts)
        if zh_value is None:
            # Get the English text to help with translation
            en_text = get_nested_value(en_data, key_parts) or generate_english_text(key_parts)
            zh_text = generate_chinese_translation(en_text, key_parts)
            set_nested_value(zh_data, key_parts, zh_text)
            zh_missing.append('.'.join(key_parts))
            print(f"    [ZH] Added: {'.'.join(key_parts)} = {zh_text}")

    # Save files if not dry run
    if not dry_run:
        # Ensure directories exist
        en_i18n_path.parent.mkdir(parents=True, exist_ok=True)
        zh_i18n_path.parent.mkdir(parents=True, exist_ok=True)

        # Write with proper formatting
        en_i18n_path.write_text(json.dumps(en_data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        zh_i18n_path.write_text(json.dumps(zh_data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

        if en_missing or zh_missing:
            print(f"  ✓ Updated {component_path.stem}.json")

    return len(en_missing) + len(zh_missing) > 0


def main():
    # Simple argument parsing without argparse
    dry_run = '--dry-run' in sys.argv
    category_filter = None

    for i, arg in enumerate(sys.argv):
        if arg == '--category' and i + 1 < len(sys.argv):
            category_filter = sys.argv[i + 1]

    base_path = Path('/Users/jiangwei/Python/langflow/src/lfx/src/lfx')
    components_path = base_path / 'components'
    locale_path = base_path / 'locale' / 'translations'

    # Categories to process
    categories = [
        'input_output',
        'operations',
        'manipulations',
        'security',
        'scripts'
    ]

    if category_filter:
        categories = [category_filter]

    total_fixed = 0

    for category in categories:
        print(f"\n{'='*60}")
        print(f"Processing category: {category}")
        print(f"{'='*60}")

        category_path = components_path / category
        if not category_path.exists():
            print(f"  Category not found: {category_path}")
            continue

        # Get all Python component files
        py_files = sorted(category_path.glob('*.py'))
        py_files = [f for f in py_files if f.stem not in ['__init__', '__pycache__']]

        for py_file in py_files:
            component_name = py_file.stem

            en_i18n_path = locale_path / 'en' / 'components' / category / f'{component_name}.json'
            zh_i18n_path = locale_path / 'zh' / 'components' / category / f'{component_name}.json'

            try:
                if fix_i18n_files(py_file, en_i18n_path, zh_i18n_path, dry_run):
                    total_fixed += 1
            except Exception as e:
                print(f"  ✗ Error processing {component_name}: {e}")

    print(f"\n{'='*60}")
    if dry_run:
        print(f"Dry run complete. {total_fixed} files would be modified.")
    else:
        print(f"Fixed {total_fixed} component i18n files.")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
