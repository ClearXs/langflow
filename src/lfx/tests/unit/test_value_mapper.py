import pytest
import json
from lfx.components.data.value_mapper import ValueMapperComponent
from langflow.schema import Data


class TestValueMapperComponent:

    @pytest.fixture
    def component(self):
        return ValueMapperComponent()

    @pytest.fixture
    def sample_data(self):
        return [
            Data(data={"id": 1, "status": "active", "category": "A", "score": 85}),
            Data(data={"id": 2, "status": "inactive", "category": "B", "score": 92}),
            Data(data={"id": 3, "status": "pending", "category": "A", "score": 78}),
            Data(data={"id": 4, "status": "active", "category": "C", "score": 95}),
            Data(data={"id": 5, "status": "", "category": None, "score": 0}),  # Empty values
        ]

    def test_simple_mapping(self, component, sample_data):
        component.data = sample_data
        component.mapping_strategy = "simple"
        component.target_fields = '["status"]'
        component.value_mappings = '{"active": "enabled", "inactive": "disabled", "pending": "waiting"}'

        result = component.map_values()

        assert result.data[0].data["status"] == "enabled"
        assert result.data[1].data["status"] == "disabled"
        assert result.data[2].data["status"] == "waiting"
        assert result.data[3].data["status"] == "enabled"

    def test_conditional_mapping(self, component, sample_data):
        component.data = sample_data
        component.mapping_strategy = "conditional"
        component.target_fields = '["grade"]'
        component.conditional_rules = '''[
            {"condition": "score >= 90", "value": "A"},
            {"condition": "score >= 80", "value": "B"},
            {"condition": "score >= 70", "value": "C"},
            {"condition": "score < 70", "value": "F"}
        ]'''

        result = component.map_values()

        assert result.data[0].data["grade"] == "B"  # score 85
        assert result.data[1].data["grade"] == "A"  # score 92
        assert result.data[2].data["grade"] == "C"  # score 78
        assert result.data[3].data["grade"] == "A"  # score 95
        assert result.data[4].data["grade"] == "F"  # score 0

    def test_calculated_mapping(self, component, sample_data):
        component.data = sample_data
        component.mapping_strategy = "calculated"
        component.target_fields = '["bonus"]'
        component.calculated_expressions = '{"bonus": "score * 0.1 if status == \'active\' else 0"}'

        result = component.map_values()

        assert result.data[0].data["bonus"] == 8.5  # active, score 85
        assert result.data[1].data["bonus"] == 0    # inactive
        assert result.data[3].data["bonus"] == 9.5  # active, score 95

    def test_lookup_table_mapping(self, component, sample_data):
        component.data = sample_data
        component.mapping_strategy = "lookup"
        component.target_fields = '["category"]'
        component.lookup_table = '''[
            {"code": "A", "name": "Premium"},
            {"code": "B", "name": "Standard"},
            {"code": "C", "name": "Basic"}
        ]'''
        component.lookup_key_field = "code"
        component.lookup_value_field = "name"

        result = component.map_values()

        assert result.data[0].data["category"] == "Premium"   # A
        assert result.data[1].data["category"] == "Standard"  # B
        assert result.data[3].data["category"] == "Basic"     # C

    def test_regex_mapping(self, component):
        email_data = [
            Data(data={"id": 1, "email": "user@gmail.com"}),
            Data(data={"id": 2, "email": "admin@company.org"}),
            Data(data={"id": 3, "email": "test@yahoo.com"}),
        ]

        component.data = email_data
        component.mapping_strategy = "regex"
        component.target_fields = '["domain_type"]'
        component.regex_patterns = '''{
            ".*@gmail\\.com": "Personal",
            ".*@.*\\.org": "Organization",
            ".*@yahoo\\.com": "Personal"
        }'''

        result = component.map_values()

        assert result.data[0].data["domain_type"] == "Personal"     # gmail
        assert result.data[1].data["domain_type"] == "Organization" # .org
        assert result.data[2].data["domain_type"] == "Personal"     # yahoo

    def test_case_sensitivity(self, component, sample_data):
        component.data = sample_data
        component.mapping_strategy = "simple"
        component.target_fields = '["status"]'
        component.value_mappings = '{"ACTIVE": "enabled"}'
        component.case_sensitive = False

        result = component.map_values()

        # Should match "active" with "ACTIVE" mapping due to case insensitivity
        assert result.data[0].data["status"] == "enabled"

    def test_preserve_unmapped_values(self, component, sample_data):
        component.data = sample_data
        component.mapping_strategy = "simple"
        component.target_fields = '["status"]'
        component.value_mappings = '{"active": "enabled"}'  # Only maps active
        component.preserve_unmapped = True

        result = component.map_values()

        assert result.data[0].data["status"] == "enabled"  # Mapped
        assert result.data[1].data["status"] == "inactive"  # Preserved (unmapped)
        assert result.data[2].data["status"] == "pending"   # Preserved (unmapped)

    def test_default_value(self, component, sample_data):
        component.data = sample_data
        component.mapping_strategy = "simple"
        component.target_fields = '["status"]'
        component.value_mappings = '{"active": "enabled"}'
        component.preserve_unmapped = False
        component.default_value = "unknown"

        result = component.map_values()

        assert result.data[0].data["status"] == "enabled"  # Mapped
        assert result.data[1].data["status"] == "unknown"  # Default
        assert result.data[2].data["status"] == "unknown"  # Default

    def test_create_new_fields(self, component, sample_data):
        component.data = sample_data
        component.mapping_strategy = "simple"
        component.target_fields = '["status"]'
        component.value_mappings = '{"active": "enabled", "inactive": "disabled"}'
        component.create_new_fields = True
        component.new_field_suffix = "_mapped"

        result = component.map_values()

        # Original fields should be preserved
        assert result.data[0].data["status"] == "active"
        # New mapped fields should be created
        assert result.data[0].data["status_mapped"] == "enabled"
        assert result.data[1].data["status_mapped"] == "disabled"

    def test_all_fields_when_target_empty(self, component, sample_data):
        component.data = sample_data
        component.mapping_strategy = "simple"
        component.target_fields = '[]'  # Empty means all fields
        component.value_mappings = '{"A": "Alpha", "B": "Beta"}'

        result = component.map_values()

        # Should process all string fields
        assert result.data[0].data["category"] == "Alpha"
        assert result.data[1].data["category"] == "Beta"

    def test_strict_mode_unmapped_value(self, component, sample_data):
        component.data = sample_data
        component.mapping_strategy = "simple"
        component.target_fields = '["status"]'
        component.value_mappings = '{"active": "enabled"}'
        component.strict_mode = True

        with pytest.raises(ValueError, match="Unmapped value"):
            component.map_values()

    def test_mapping_report(self, component, sample_data):
        component.data = sample_data
        component.mapping_strategy = "simple"
        component.target_fields = '["status"]'
        component.value_mappings = '{"active": "enabled", "inactive": "disabled"}'

        # Run mapping first
        component.map_values()

        # Get mapping report
        report = component.get_mapping_report()

        assert "total_records" in report.data
        assert "modified_records" in report.data
        assert "total_mappings" in report.data
        assert "fields_processed" in report.data

        assert report.data["total_records"] == 5
        assert report.data["modified_records"] >= 2
        assert report.data["total_mappings"] >= 2

    def test_unmapped_values_output(self, component, sample_data):
        component.data = sample_data
        component.mapping_strategy = "simple"
        component.target_fields = '["status"]'
        component.value_mappings = '{"active": "enabled"}'
        component.preserve_unmapped = True

        # Run mapping first
        component.map_values()

        # Get unmapped values
        unmapped = component.get_unmapped_values()

        assert "unmapped_values" in unmapped.data
        unmapped_list = unmapped.data["unmapped_values"]
        assert "inactive" in unmapped_list
        assert "pending" in unmapped_list

    def test_empty_data_handling(self, component):
        component.data = []

        with pytest.raises(ValueError, match="empty"):
            component.map_values()

    def test_invalid_json_value_mappings(self, component, sample_data):
        component.data = sample_data
        component.mapping_strategy = "simple"
        component.value_mappings = "invalid json"

        with pytest.raises(json.JSONDecodeError):
            component.map_values()

    def test_invalid_expression(self, component, sample_data):
        component.data = sample_data
        component.mapping_strategy = "calculated"
        component.calculated_expressions = '{"result": "invalid_syntax +"}'

        with pytest.raises(Exception):  # Should raise expression evaluation error
            component.map_values()

    def test_lookup_table_missing_fields(self, component, sample_data):
        component.data = sample_data
        component.mapping_strategy = "lookup"
        component.lookup_table = '[{"wrong_field": "A", "name": "Alpha"}]'
        component.lookup_key_field = "code"  # Field doesn't exist in table
        component.lookup_value_field = "name"

        with pytest.raises(ValueError, match="Lookup table error"):
            component.map_values()

    def test_single_record(self, component):
        single_data = [Data(data={"id": 1, "status": "active"})]
        component.data = single_data
        component.mapping_strategy = "simple"
        component.target_fields = '["status"]'
        component.value_mappings = '{"active": "enabled"}'

        result = component.map_values()

        assert len(result.data) == 1
        assert result.data[0].data["status"] == "enabled"

    def test_nested_field_access_in_expressions(self, component):
        nested_data = [
            Data(data={
                "id": 1,
                "user": {"name": "John", "age": 25},
                "scores": [80, 90, 85]
            })
        ]

        component.data = nested_data
        component.mapping_strategy = "calculated"
        component.target_fields = '["summary"]'
        component.calculated_expressions = '{"summary": "f\"{user[\'name\']} is {user[\'age\']} years old\""}'

        result = component.map_values()

        assert result.data[0].data["summary"] == "John is 25 years old"

    def test_multiple_field_mapping(self, component, sample_data):
        component.data = sample_data
        component.mapping_strategy = "simple"
        component.target_fields = '["status", "category"]'
        component.value_mappings = '''{
            "active": "enabled",
            "inactive": "disabled",
            "A": "Alpha",
            "B": "Beta",
            "C": "Gamma"
        }'''

        result = component.map_values()

        # Both fields should be mapped
        assert result.data[0].data["status"] == "enabled"
        assert result.data[0].data["category"] == "Alpha"
        assert result.data[1].data["status"] == "disabled"
        assert result.data[1].data["category"] == "Beta"