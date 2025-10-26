"""Unit tests for ETLFieldValueMappingComponent with enhanced features."""

import pytest

from lfx.components.manipulations.field_value_mapping import ETLFieldValueMappingComponent
from lfx.schema import Data


class TestETLFieldValueMappingComponent:
    """Test suite for Field Value Mapping component."""

    def test_basic_equal_mapping(self):
        """Test basic equal (=) operator mapping."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"gender_code": "1", "status": "2"}),
                Data(data={"gender_code": "0", "status": "1"}),
            ],
            mapping_rules=[
                {
                    "input_field": "gender_code",
                    "operator": "=",
                    "compare_value": "1",
                    "replacement_value": "Male",
                    "output_field": "gender_text",
                },
                {
                    "input_field": "gender_code",
                    "operator": "=",
                    "compare_value": "0",
                    "replacement_value": "Female",
                    "output_field": "gender_text",
                },
            ],
        )

        result = component.map_field_values()

        assert len(result) == 2
        assert result[0].data["gender_text"] == "Male"
        assert result[1].data["gender_text"] == "Female"
        # Original fields preserved
        assert result[0].data["gender_code"] == "1"
        assert result[1].data["gender_code"] == "0"

    def test_multiple_fields_mapping(self):
        """Test mapping multiple fields in single component."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"gender_code": "1", "status": "2"}),
                Data(data={"gender_code": "0", "status": "1"}),
            ],
            mapping_rules=[
                {
                    "input_field": "gender_code",
                    "operator": "=",
                    "compare_value": "1",
                    "replacement_value": "Male",
                    "output_field": "gender_text",
                },
                {
                    "input_field": "gender_code",
                    "operator": "=",
                    "compare_value": "0",
                    "replacement_value": "Female",
                    "output_field": "gender_text",
                },
                {
                    "input_field": "status",
                    "operator": "=",
                    "compare_value": "1",
                    "replacement_value": "Pending",
                    "output_field": "status_text",
                },
                {
                    "input_field": "status",
                    "operator": "=",
                    "compare_value": "2",
                    "replacement_value": "Active",
                    "output_field": "status_text",
                },
            ],
        )

        result = component.map_field_values()

        assert len(result) == 2
        # First record
        assert result[0].data["gender_text"] == "Male"
        assert result[0].data["status_text"] == "Active"
        # Second record
        assert result[1].data["gender_text"] == "Female"
        assert result[1].data["status_text"] == "Pending"

    def test_regex_operator(self):
        """Test regex operator for pattern matching."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"email": "john@gmail.com"}),
                Data(data={"email": "alice@yahoo.com"}),
                Data(data={"email": "bob@company.org"}),
                Data(data={"email": "invalid-email"}),
            ],
            mapping_rules=[
                {
                    "input_field": "email",
                    "operator": "regex",
                    "compare_value": r".*@gmail\.com$",
                    "replacement_value": "Gmail User",
                    "output_field": "email_provider",
                },
                {
                    "input_field": "email",
                    "operator": "regex",
                    "compare_value": r".*@yahoo\.com$",
                    "replacement_value": "Yahoo User",
                    "output_field": "email_provider",
                },
                {
                    "input_field": "email",
                    "operator": "regex",
                    "compare_value": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                    "replacement_value": "Valid Email",
                    "output_field": "email_status",
                },
            ],
        )

        result = component.map_field_values()

        assert len(result) == 4
        assert result[0].data.get("email_provider") == "Gmail User"
        assert result[1].data.get("email_provider") == "Yahoo User"
        assert result[2].data.get("email_provider") is None  # No matching provider rule
        assert result[3].data.get("email_status") is None  # Invalid email format

    def test_javascript_script_mapping(self):
        """Test JavaScript script-based mapping."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"age": 25, "name": "John", "score": 85}),
                Data(data={"age": 17, "name": "Alice", "score": 92}),
                Data(data={"age": 70, "name": "Bob", "score": 78}),
            ],
            mapping_rules=[],  # No rules, using script only
            enable_script=True,
            script_type="javascript",
            script_content="""
// Age category mapping
if (row.age < 18) {
    row.age_category = 'Minor';
} else if (row.age >= 65) {
    row.age_category = 'Senior';
} else {
    row.age_category = 'Adult';
}

// Grade mapping based on score
row.grade = row.score >= 90 ? 'A' : row.score >= 80 ? 'B' : 'C';

// Name length category
row.name_length = row.name.length > 4 ? 'Long' : 'Short';
""",
        )

        result = component.map_field_values()

        assert len(result) == 3

        # First record (age 25)
        assert result[0].data.get("age_category") == "Adult"
        assert result[0].data.get("grade") == "B"
        assert result[0].data.get("name_length") == "Short"

        # Second record (age 17)
        assert result[1].data.get("age_category") == "Minor"
        assert result[1].data.get("grade") == "A"
        assert result[1].data.get("name_length") == "Long"

        # Third record (age 70)
        assert result[2].data.get("age_category") == "Senior"
        assert result[2].data.get("grade") == "C"
        assert result[2].data.get("name_length") == "Short"

    def test_python_script_mapping(self):
        """Test Python script-based mapping."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"product": "iPhone", "price": 999, "quantity": 2}),
                Data(data={"product": "Laptop", "price": 1500, "quantity": 1}),
                Data(data={"product": "Mouse", "price": 25, "quantity": 5}),
            ],
            mapping_rules=[],  # No rules, using script only
            enable_script=True,
            script_type="python",
            script_content="""
# Calculate total price
result['total'] = row.get('price', 0) * row.get('quantity', 1)

# Determine price category
if row.get('price', 0) >= 1000:
    result['price_category'] = 'Expensive'
elif row.get('price', 0) >= 100:
    result['price_category'] = 'Moderate'
else:
    result['price_category'] = 'Cheap'

# Add discount based on quantity
if row.get('quantity', 0) >= 5:
    result['discount'] = '20%'
elif row.get('quantity', 0) >= 2:
    result['discount'] = '10%'
else:
    result['discount'] = '0%'
""",
        )

        result = component.map_field_values()

        assert len(result) == 3

        # First record
        assert result[0].data.get("total") == 1998
        assert result[0].data.get("price_category") == "Moderate"
        assert result[0].data.get("discount") == "10%"

        # Second record
        assert result[1].data.get("total") == 1500
        assert result[1].data.get("price_category") == "Expensive"
        assert result[1].data.get("discount") == "0%"

        # Third record
        assert result[2].data.get("total") == 125
        assert result[2].data.get("price_category") == "Cheap"
        assert result[2].data.get("discount") == "20%"

    def test_combined_rules_and_script(self):
        """Test combination of mapping rules and script."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"status": "1", "priority": "high", "count": 10}),
                Data(data={"status": "2", "priority": "low", "count": 5}),
                Data(data={"status": "3", "priority": "medium", "count": 15}),
            ],
            mapping_rules=[
                {
                    "input_field": "status",
                    "operator": "=",
                    "compare_value": "1",
                    "replacement_value": "Active",
                    "output_field": "status_text",
                },
                {
                    "input_field": "status",
                    "operator": "=",
                    "compare_value": "2",
                    "replacement_value": "Inactive",
                    "output_field": "status_text",
                },
                {
                    "input_field": "status",
                    "operator": "=",
                    "compare_value": "3",
                    "replacement_value": "Pending",
                    "output_field": "status_text",
                },
            ],
            enable_script=True,
            script_type="javascript",
            script_content="""
// Add urgency based on priority and count
if (row.priority === 'high' && row.count > 5) {
    row.urgency = 'Critical';
} else if (row.priority === 'high' || row.count > 10) {
    row.urgency = 'High';
} else {
    row.urgency = 'Normal';
}
""",
        )

        result = component.map_field_values()

        assert len(result) == 3

        # First record: Rules map status, script adds urgency
        assert result[0].data["status_text"] == "Active"
        assert result[0].data["urgency"] == "Critical"

        # Second record
        assert result[1].data["status_text"] == "Inactive"
        assert result[1].data["urgency"] == "Normal"

        # Third record
        assert result[2].data["status_text"] == "Pending"
        assert result[2].data["urgency"] == "High"

    def test_contains_operator(self):
        """Test contains operator for string matching."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"product_name": "iPhone 15 Pro"}),
                Data(data={"product_name": "Samsung Galaxy S24"}),
                Data(data={"product_name": "Google Pixel 8"}),
            ],
            mapping_rules=[
                {
                    "input_field": "product_name",
                    "operator": "contains",
                    "compare_value": "iPhone",
                    "replacement_value": "Apple",
                    "output_field": "brand",
                },
                {
                    "input_field": "product_name",
                    "operator": "contains",
                    "compare_value": "Samsung",
                    "replacement_value": "Samsung",
                    "output_field": "brand",
                },
                {
                    "input_field": "product_name",
                    "operator": "contains",
                    "compare_value": "Google",
                    "replacement_value": "Google",
                    "output_field": "brand",
                },
            ],
        )

        result = component.map_field_values()

        assert len(result) == 3
        assert result[0].data["brand"] == "Apple"
        assert result[1].data["brand"] == "Samsung"
        assert result[2].data["brand"] == "Google"

    def test_greater_than_operator(self):
        """Test greater than (>) operator with first-match-wins behavior."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"age": "25", "score": "85"}),
                Data(data={"age": "15", "score": "92"}),
                Data(data={"age": "70", "score": "78"}),
            ],
            mapping_rules=[
                # Order matters: check Senior first (>= 65), then Adult (>= 18)
                {
                    "input_field": "age",
                    "operator": ">=",
                    "compare_value": "65",
                    "replacement_value": "Senior",
                    "output_field": "age_group",
                },
                {
                    "input_field": "age",
                    "operator": ">=",
                    "compare_value": "18",
                    "replacement_value": "Adult",
                    "output_field": "age_group",
                },
                {
                    "input_field": "score",
                    "operator": ">=",
                    "compare_value": "90",
                    "replacement_value": "A",
                    "output_field": "grade",
                },
            ],
        )

        result = component.map_field_values()

        assert len(result) == 3
        assert result[0].data["age_group"] == "Adult"  # age 25: >= 65 false, >= 18 true
        assert result[1].data.get("age_group") is None  # age 15: both false
        assert result[2].data["age_group"] == "Senior"  # age 70: >= 65 true (first match)
        assert result[1].data["grade"] == "A"  # score 92 >= 90

    def test_starts_with_operator(self):
        """Test starts_with operator."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"code": "ERR_001"}),
                Data(data={"code": "WARN_002"}),
                Data(data={"code": "INFO_003"}),
            ],
            mapping_rules=[
                {
                    "input_field": "code",
                    "operator": "starts_with",
                    "compare_value": "ERR",
                    "replacement_value": "Error",
                    "output_field": "level",
                },
                {
                    "input_field": "code",
                    "operator": "starts_with",
                    "compare_value": "WARN",
                    "replacement_value": "Warning",
                    "output_field": "level",
                },
                {
                    "input_field": "code",
                    "operator": "starts_with",
                    "compare_value": "INFO",
                    "replacement_value": "Info",
                    "output_field": "level",
                },
            ],
        )

        result = component.map_field_values()

        assert len(result) == 3
        assert result[0].data["level"] == "Error"
        assert result[1].data["level"] == "Warning"
        assert result[2].data["level"] == "Info"

    def test_ends_with_operator(self):
        """Test ends_with operator."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"filename": "document.pdf"}),
                Data(data={"filename": "image.jpg"}),
                Data(data={"filename": "data.csv"}),
            ],
            mapping_rules=[
                {
                    "input_field": "filename",
                    "operator": "ends_with",
                    "compare_value": ".pdf",
                    "replacement_value": "PDF Document",
                    "output_field": "file_type",
                },
                {
                    "input_field": "filename",
                    "operator": "ends_with",
                    "compare_value": ".jpg",
                    "replacement_value": "JPEG Image",
                    "output_field": "file_type",
                },
                {
                    "input_field": "filename",
                    "operator": "ends_with",
                    "compare_value": ".csv",
                    "replacement_value": "CSV Data",
                    "output_field": "file_type",
                },
            ],
        )

        result = component.map_field_values()

        assert len(result) == 3
        assert result[0].data["file_type"] == "PDF Document"
        assert result[1].data["file_type"] == "JPEG Image"
        assert result[2].data["file_type"] == "CSV Data"

    def test_in_operator(self):
        """Test in operator with comma-separated list."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"status_code": "1"}),
                Data(data={"status_code": "2"}),
                Data(data={"status_code": "5"}),
            ],
            mapping_rules=[
                {
                    "input_field": "status_code",
                    "operator": "in",
                    "compare_value": "1,2,3",
                    "replacement_value": "Valid",
                    "output_field": "validation",
                },
            ],
        )

        result = component.map_field_values()

        assert len(result) == 3
        assert result[0].data["validation"] == "Valid"
        assert result[1].data["validation"] == "Valid"
        assert result[2].data.get("validation") is None  # status_code not in list

    def test_not_equal_operator(self):
        """Test not equal (!=) operator."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"status": "active"}),
                Data(data={"status": "inactive"}),
                Data(data={"status": "pending"}),
            ],
            mapping_rules=[
                {
                    "input_field": "status",
                    "operator": "!=",
                    "compare_value": "active",
                    "replacement_value": "Not Active",
                    "output_field": "status_label",
                },
            ],
        )

        result = component.map_field_values()

        assert len(result) == 3
        assert result[0].data.get("status_label") is None  # status == active
        assert result[1].data["status_label"] == "Not Active"
        assert result[2].data["status_label"] == "Not Active"

    def test_overwrite_original_field(self):
        """Test overwriting original field when output_field == input_field."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"status": "1"}),
                Data(data={"status": "2"}),
            ],
            mapping_rules=[
                {
                    "input_field": "status",
                    "operator": "=",
                    "compare_value": "1",
                    "replacement_value": "Active",
                    "output_field": "status",  # Same as input_field
                },
                {
                    "input_field": "status",
                    "operator": "=",
                    "compare_value": "2",
                    "replacement_value": "Inactive",
                    "output_field": "status",
                },
            ],
        )

        result = component.map_field_values()

        assert len(result) == 2
        assert result[0].data["status"] == "Active"  # Overwritten
        assert result[1].data["status"] == "Inactive"  # Overwritten

    def test_missing_field_in_data(self):
        """Test handling of missing field in data."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"id": "1", "name": "John"}),  # gender_code missing
            ],
            mapping_rules=[
                {
                    "input_field": "gender_code",
                    "operator": "=",
                    "compare_value": "1",
                    "replacement_value": "Male",
                    "output_field": "gender_text",
                },
            ],
        )

        result = component.map_field_values()

        assert len(result) == 1
        assert result[0].data.get("gender_text") is None  # No mapping applied
        assert result[0].data["id"] == "1"
        assert result[0].data["name"] == "John"

    def test_no_matching_rule(self):
        """Test when no rule matches the field value."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"status": "999"}),  # No rule for this value
            ],
            mapping_rules=[
                {
                    "input_field": "status",
                    "operator": "=",
                    "compare_value": "1",
                    "replacement_value": "Active",
                    "output_field": "status_text",
                },
            ],
        )

        result = component.map_field_values()

        assert len(result) == 1
        assert result[0].data.get("status_text") is None  # No match
        assert result[0].data["status"] == "999"  # Original preserved

    def test_empty_data_input(self):
        """Test handling of empty data input."""
        component = ETLFieldValueMappingComponent(
            data_input=[],
            mapping_rules=[
                {
                    "input_field": "field1",
                    "operator": "=",
                    "compare_value": "1",
                    "replacement_value": "Value1",
                    "output_field": "field2",
                },
            ],
        )

        result = component.map_field_values()

        assert len(result) == 0  # Empty input returns empty output

    def test_missing_mapping_rules_error(self):
        """Test error when mapping rules are missing and script is disabled."""
        component = ETLFieldValueMappingComponent(
            data_input=[Data(data={"field1": "value1"})],
            mapping_rules=[],
            enable_script=False,
        )

        with pytest.raises(ValueError):
            component.map_field_values()

    def test_script_only_mode(self):
        """Test that script can work without mapping rules."""
        component = ETLFieldValueMappingComponent(
            data_input=[Data(data={"value": 10})],
            mapping_rules=[],  # No mapping rules
            enable_script=True,
            script_type="python",
            script_content="result['doubled'] = row.get('value', 0) * 2",
        )

        result = component.map_field_values()

        assert len(result) == 1
        assert result[0].data["doubled"] == 20

    def test_missing_required_fields_error(self):
        """Test error when rule is missing required fields."""
        component = ETLFieldValueMappingComponent(
            data_input=[Data(data={"field1": "value1"})],
            mapping_rules=[
                {
                    "input_field": "field1",
                    "operator": "=",
                    "compare_value": "value1",
                    "replacement_value": "new_value",
                    # Missing output_field
                },
            ],
        )

        with pytest.raises(ValueError):
            component.map_field_values()

    def test_complex_multi_field_scenario(self):
        """Test complex scenario with multiple fields and conditions."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"id": "1", "gender": "M", "age": "25", "status": "active"}),
                Data(data={"id": "2", "gender": "F", "age": "17", "status": "inactive"}),
                Data(data={"id": "3", "gender": "M", "age": "70", "status": "active"}),
            ],
            mapping_rules=[
                # Gender mapping
                {
                    "input_field": "gender",
                    "operator": "=",
                    "compare_value": "M",
                    "replacement_value": "Male",
                    "output_field": "gender_text",
                },
                {
                    "input_field": "gender",
                    "operator": "=",
                    "compare_value": "F",
                    "replacement_value": "Female",
                    "output_field": "gender_text",
                },
                # Age group mapping - order matters!
                {
                    "input_field": "age",
                    "operator": ">=",
                    "compare_value": "65",
                    "replacement_value": "Senior",
                    "output_field": "age_group",
                },
                {
                    "input_field": "age",
                    "operator": ">=",
                    "compare_value": "18",
                    "replacement_value": "Adult",
                    "output_field": "age_group",
                },
                # Status mapping
                {
                    "input_field": "status",
                    "operator": "=",
                    "compare_value": "active",
                    "replacement_value": "Active",
                    "output_field": "status_label",
                },
                {
                    "input_field": "status",
                    "operator": "=",
                    "compare_value": "inactive",
                    "replacement_value": "Inactive",
                    "output_field": "status_label",
                },
            ],
        )

        result = component.map_field_values()

        assert len(result) == 3

        # First record: Male, Adult (25 >= 18, first match), Active
        assert result[0].data["gender_text"] == "Male"
        assert result[0].data["age_group"] == "Adult"  # >= 18 matches, >= 65 false
        assert result[0].data["status_label"] == "Active"

        # Second record: Female, no age_group (17 < 18), Inactive
        assert result[1].data["gender_text"] == "Female"
        assert result[1].data.get("age_group") is None
        assert result[1].data["status_label"] == "Inactive"

        # Third record: Male, Senior (70 >= 65, first match wins), Active
        assert result[2].data["gender_text"] == "Male"
        assert result[2].data["age_group"] == "Senior"  # >= 65 matched first
        assert result[2].data["status_label"] == "Active"

    def test_numeric_string_comparison(self):
        """Test numeric comparison with string values and first-match-wins."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"score": "85"}),
                Data(data={"score": "92"}),
                Data(data={"score": "78"}),
            ],
            mapping_rules=[
                # Order matters: check highest grade first
                {
                    "input_field": "score",
                    "operator": ">=",
                    "compare_value": "90",
                    "replacement_value": "A",
                    "output_field": "grade",
                },
                {
                    "input_field": "score",
                    "operator": ">=",
                    "compare_value": "80",
                    "replacement_value": "B",
                    "output_field": "grade",
                },
                {
                    "input_field": "score",
                    "operator": ">=",
                    "compare_value": "70",
                    "replacement_value": "C",
                    "output_field": "grade",
                },
            ],
        )

        result = component.map_field_values()

        assert len(result) == 3
        assert result[0].data["grade"] == "B"  # 85: >= 90 false, >= 80 true (first match)
        assert result[1].data["grade"] == "A"  # 92: >= 90 true (first match)
        assert result[2].data["grade"] == "C"  # 78: >= 90 false, >= 80 false, >= 70 true

    def test_invalid_regex_pattern(self):
        """Test handling of invalid regex pattern."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"text": "test"}),
            ],
            mapping_rules=[
                {
                    "input_field": "text",
                    "operator": "regex",
                    "compare_value": "[invalid(regex",  # Invalid regex
                    "replacement_value": "matched",
                    "output_field": "result",
                },
            ],
        )

        result = component.map_field_values()

        assert len(result) == 1
        assert result[0].data.get("result") is None  # No match due to invalid regex
        assert result[0].data["text"] == "test"  # Original preserved

    def test_complex_regex_patterns(self):
        """Test complex regex patterns for advanced matching."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"phone": "+1-555-123-4567"}),
                Data(data={"phone": "555.123.4567"}),
                Data(data={"phone": "(555) 123-4567"}),
                Data(data={"phone": "invalid"}),
            ],
            mapping_rules=[
                {
                    "input_field": "phone",
                    "operator": "regex",
                    "compare_value": r"^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$",
                    "replacement_value": "Valid US Phone",
                    "output_field": "phone_status",
                },
            ],
        )

        result = component.map_field_values()

        assert len(result) == 4
        assert result[0].data.get("phone_status") == "Valid US Phone"
        assert result[1].data.get("phone_status") == "Valid US Phone"
        assert result[2].data.get("phone_status") == "Valid US Phone"
        assert result[3].data.get("phone_status") is None  # Invalid format
