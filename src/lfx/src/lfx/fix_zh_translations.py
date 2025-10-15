#!/usr/bin/env python3
"""
Script to translate all remaining English text in ZH i18n files.
"""

import json
from pathlib import Path
from typing import Dict, Any


# Comprehensive translation dictionary
TRANSLATIONS = {
    # Display names
    'Data Input': '数据输入',
    'Data Output': '数据输出',
    'Key Columns': '关键列',
    'Keep Strategy': '保留策略',
    'Ignore Null': '忽略空值',
    'Case Sensitive': '区分大小写',
    'Trim Whitespace': '去除空白',
    'Join Type': '连接类型',
    'Join Key': '连接键',
    'Left Key': '左侧键',
    'Right Key': '右侧键',
    'Left Stream': '左侧数据流',
    'Right Stream': '右侧数据流',
    'Left Prefix': '左侧前缀',
    'Right Prefix': '右侧前缀',
    'Join Conditions': '连接条件',
    'Group Keys': '分组键',
    'Group By Columns': '分组列',
    'Aggregations': '聚合',
    'Aggregation Functions': '聚合函数',
    'Drop NA': '删除空值',
    'Sort Results': '排序结果',
    'Stream 1': '数据流1',
    'Stream 2': '数据流2',
    'Stream 3': '数据流3',
    'Stream 4': '数据流4',
    'Stream 5': '数据流5',
    'Include Source Info': '包含来源信息',
    'Source Column Name': '来源列名',
    'Source Column': '来源列',
    'Align Schemas': '对齐模式',
    'Drop Duplicates': '删除重复',
    'Remove Duplicates': '删除重复',
    'Remove Null Rows': '删除空值行',
    'Remove Special Characters': '删除特殊字符',
    'Normalize Case': '标准化大小写',
    'Case Type': '大小写类型',
    'Field Mappings': '字段映射',
    'Field Name': '字段名',
    'Drop Unmapped Fields': '删除未映射字段',
    'Drop Unmapped': '删除未映射',
    'Source Field': '源字段',
    'New Field Names': '新字段名',
    'Max Splits': '最大拆分数',
    'Drop Source Field': '删除源字段',
    'Value Mappings': '值映射',
    'Default Value': '默认值',
    'Merge Configurations': '合并配置',
    'Drop Source Fields': '删除源字段',
    'Fields to Process': '要处理的字段',
    'Operation': '操作',
    'Use Base64': '使用Base64',
    'Masking Rules': '脱敏规则',
    'Capture Output': '捕获输出',
    'Working Directory': '工作目录',
    'Execution Timeout': '执行超时',

    # Info messages
    'Input data to deduplicate': '要去重的输入数据',
    'Columns to identify duplicates': '用于识别重复的列',
    'Which duplicate to keep': '保留哪条重复记录',
    'Ignore null values in comparison': '比较时忽略空值',
    'Case-sensitive comparison': '比较时区分大小写',
    'Trim whitespace before comparison': '比较前去除首尾空白字符',
    'No input data provided': '未提供输入数据',
    'Input data to transform': '要转换的输入数据',
    'Input data to clean': '要清洗的输入数据',
    'Input data to mask': '要脱敏的输入数据',
    'Input data to process': '要处理的输入数据',
    'Input data to group': '要分组的输入数据',
    'Type of join operation': '连接操作类型',
    'Column name for join key': '连接键的列名',
    'Left join key column': '左侧连接键列',
    'Right join key column': '右侧连接键列',
    'Fields to join on': '用于连接的字段',
    'Prefix for left stream columns': '左侧数据流列的前缀',
    'Prefix for right stream columns': '右侧数据流列的前缀',
    'Remove duplicate rows after join': '连接后删除重复行',
    'First data stream': '第一个数据流',
    'Second data stream': '第二个数据流',
    'Third data stream': '第三个数据流',
    'Fourth data stream': '第四个数据流',
    'Fifth data stream': '第五个数据流',
    'Add source stream identifier': '添加来源数据流标识',
    'Column name for stream source': '数据流来源的列名',
    'Align column schemas across streams': '对齐各数据流的列模式',
    'Remove duplicate rows': '删除重复的行',
    'Columns for grouping': '用于分组的列',
    'Columns to group by': '用于分组的列',
    'Aggregation operations': '聚合操作',
    'Aggregation functions to apply': '要应用的聚合函数',
    'Exclude rows with null values': '排除包含空值的行',
    'Sort by grouping columns': '按分组列排序',
    'Remove rows with null values': '删除包含空值的行',
    'Remove special characters': '删除特殊字符',
    'Convert text case': '转换文本大小写',
    'Type of case conversion': '大小写转换类型',
    'Source to target field mappings': '源字段到目标字段的映射',
    'Remove fields not in mapping': '删除不在映射中的字段',
    'Field to split': '要拆分的字段',
    'Names for new fields (comma-separated)': '新字段的名称(逗号分隔)',
    'Split delimiter': '拆分分隔符',
    'Maximum number of splits (-1 = unlimited)': '最大拆分数(-1表示不限制)',
    'Remove source field after split': '拆分后删除源字段',
    'Field to apply mapping': '应用映射的字段',
    'Source to target value mappings': '源值到目标值的映射',
    'Default for unmapped values': '未映射值的默认值',
    'Fields to merge and separators': '要合并的字段和分隔符',
    'Remove source fields after merge': '合并后删除源字段',
    'Encryption/decryption key': '加密/解密密钥',
    'Fields to encrypt/decrypt': '要加密/解密的字段',
    'Encrypt or decrypt': '加密或解密',
    'Encode result with Base64': '使用Base64编码结果',
    'Fields and masking types': '字段和脱敏类型',
    'Python code to execute': 'Python代码执行',
    "Available as 'data_input' variable": "作为'data_input'变量可用",
    'Capture print output': '捕获打印输出',
    'Shell commands to execute': 'Shell命令执行',
    'Optional data input': '可选数据输入',
    'Capture stdout/stderr': '捕获标准输出/错误输出',
    'Script working directory': '脚本工作目录',

    # Error messages
    'No input data provided': '未提供输入数据',
    'Both streams are required': '两个数据流都是必需的',
    'Join conditions are required': '连接条件是必需的',
    'Group by columns are required': '分组列是必需的',
    'Aggregations are required': '聚合是必需的',
    'Field mappings are required': '字段映射是必需的',
    'Source field is required': '源字段是必需的',
    'Field not found: {field}': '字段未找到: {field}',
    'Value mappings are required': '值映射是必需的',
    'Merge configurations are required': '合并配置是必需的',
    'Encryption configuration is required': '加密配置是必需的',
    'Masking rules are required': '脱敏规则是必需的',
    'Script is required': '脚本是必需的',
    'Script execution timed out': '脚本执行超时',
    'At least one stream is required': '至少需要一个数据流',
    'Audit table not found': '审计表未找到',
    'Invalid CDC mode': '无效的CDC模式',
    'No data to write': '没有要写入的数据',
    'Key columns required for upsert': 'Upsert操作需要键列',

    # Additional display names
    'Auto Create Table': '自动创建表',
    'Connection String': '连接字符串',
    'Truncate First': '先清空表',
    'Write Mode': '写入模式',

    # Additional info messages
    'Create table if not exists': '如果表不存在则创建',
    'Database connection string': '数据库连接字符串',
    'Data to write': '要写入的数据',
    'Columns for upsert matching': '用于upsert匹配的列',
    'Target table name': '目标表名',
    'Clear table before writing': '写入前清空表',
    'How to write data': '如何写入数据',

    # Status messages
    'Deduplicating...': '正在去重...',
    'Joining streams...': '正在合并数据流...',
    'Grouping data...': '正在分组数据...',
    'Merging streams...': '正在合并数据流...',
    'Cleaning data...': '正在清洗数据...',
    'Mapping fields...': '正在映射字段...',
    'Splitting fields...': '正在拆分字段...',
    'Encrypting data...': '正在加密数据...',
    'Decrypting data...': '正在解密数据...',
    'Masking data...': '正在脱敏数据...',
    'Executing script...': '正在执行脚本...',
}


def translate_value(value: Any, path: str = "") -> Any:
    """Recursively translate English text in a value."""
    if isinstance(value, str):
        # Check if it's English text that needs translation
        translated = TRANSLATIONS.get(value, value)
        if translated != value:
            print(f"  Translated: {value} -> {translated}")
        return translated
    elif isinstance(value, dict):
        return {k: translate_value(v, f"{path}.{k}") for k, v in value.items()}
    elif isinstance(value, list):
        return [translate_value(item, f"{path}[]") for item in value]
    else:
        return value


def fix_zh_file(zh_file: Path):
    """Fix a single ZH i18n file by translating remaining English text."""
    try:
        with open(zh_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        original_json = json.dumps(data, ensure_ascii=False, indent=2)
        translated_data = translate_value(data)
        new_json = json.dumps(translated_data, ensure_ascii=False, indent=2)

        if original_json != new_json:
            with open(zh_file, 'w', encoding='utf-8') as f:
                f.write(new_json + '\n')
            return True
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def main():
    base_path = Path('/Users/jiangwei/Python/langflow/src/lfx/src/lfx')
    zh_base = base_path / 'locale' / 'translations' / 'zh' / 'components'

    categories = ['operations', 'manipulations', 'security', 'scripts', 'input_output']

    total_fixed = 0

    for category in categories:
        category_path = zh_base / category
        if not category_path.exists():
            continue

        print(f"\n{'='*60}")
        print(f"Processing category: {category}")
        print(f"{'='*60}")

        for zh_file in sorted(category_path.glob('*.json')):
            print(f"\nChecking {zh_file.name}...")
            if fix_zh_file(zh_file):
                total_fixed += 1
                print(f"  ✓ Updated {zh_file.name}")

    print(f"\n{'='*60}")
    print(f"Fixed {total_fixed} files")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
