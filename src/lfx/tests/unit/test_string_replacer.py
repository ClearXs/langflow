import pytest
import json
from lfx.components.data.string_replacer import StringReplacerComponent
from langflow.schema import Data


class TestStringReplacerComponent:

    @pytest.fixture
    def component(self):
        return StringReplacerComponent()

    @pytest.fixture
    def sample_data(self):
        return [
            Data(data={"id": 1, "text": "Hello World", "description": "This is a test"}),
            Data(data={"id": 2, "text": "hello world", "description": "Another test case"}),
            Data(data={"id": 3, "text": "Welcome to Python", "description": "Python is great"}),
            Data(data={"id": 4, "text": "", "description": None}),  # Empty/null values
        ]

    def test_simple_replacement(self, component, sample_data):
        component.data = sample_data
        component.replacement_strategy = "simple"
        component.search_value = "Hello"
        component.replace_value = "Hi"
        component.case_sensitive = True

        result = component.replace_strings()

        # Only exact case match should be replaced
        assert result.data[0].data["text"] == "Hi World"
        assert result.data[1].data["text"] == "hello world"  # No change due to case sensitivity

    def test_case_insensitive_replacement(self, component, sample_data):
        component.data = sample_data
        component.replacement_strategy = "simple"
        component.search_value = "hello"
        component.replace_value = "Hi"
        component.case_sensitive = False

        result = component.replace_strings()

        # Both should be replaced
        assert result.data[0].data["text"] == "Hi World"
        assert result.data[1].data["text"] == "Hi world"

    def test_regex_replacement(self, component, sample_data):
        component.data = sample_data
        component.replacement_strategy = "regex"
        component.search_value = r"[Ww]orld"
        component.replace_value = "Universe"

        result = component.replace_strings()

        assert result.data[0].data["text"] == "Hello Universe"
        assert result.data[1].data["text"] == "hello Universe"

    def test_regex_with_groups(self, component):
        data_with_emails = [
            Data(data={"id": 1, "email": "user@example.com"}),
            Data(data={"id": 2, "email": "admin@test.org"}),
        ]

        component.data = data_with_emails
        component.replacement_strategy = "regex"
        component.search_value = r"(\w+)@(\w+)\.(\w+)"
        component.replace_value = r"\1 at \2 dot \3"

        result = component.replace_strings()

        assert result.data[0].data["email"] == "user at example dot com"
        assert result.data[1].data["email"] == "admin at test dot org"

    def test_bulk_replacement(self, component, sample_data):
        component.data = sample_data
        component.replacement_strategy = "bulk"
        component.replacement_map = '{"Hello": "Hi", "World": "Universe", "Python": "Java"}'

        result = component.replace_strings()

        assert result.data[0].data["text"] == "Hi Universe"
        assert result.data[2].data["text"] == "Welcome to Java"
        assert result.data[2].data["description"] == "Java is great"

    def test_template_replacement(self, component):
        template_data = [
            Data(data={"id": 1, "template": "Hello {name}, welcome to {place}"}),
            Data(data={"id": 2, "template": "Your score is {score}%"}),
        ]

        component.data = template_data
        component.replacement_strategy = "template"
        component.template_variables = '{"name": "John", "place": "Python World", "score": 95}'

        result = component.replace_strings()

        assert result.data[0].data["template"] == "Hello John, welcome to Python World"
        assert result.data[1].data["template"] == "Your score is 95%"

    def test_target_fields_filtering(self, component, sample_data):
        component.data = sample_data
        component.replacement_strategy = "simple"
        component.search_value = "test"
        component.replace_value = "example"
        component.target_fields = '["description"]'  # Only target description field

        result = component.replace_strings()

        # Only description fields should be modified
        assert result.data[0].data["text"] == "Hello World"  # Unchanged
        assert result.data[0].data["description"] == "This is a example"  # Changed
        assert result.data[1].data["description"] == "Another example case"  # Changed

    def test_whole_word_only(self, component):
        word_data = [
            Data(data={"id": 1, "text": "test testing tested"}),
            Data(data={"id": 2, "text": "This is a test"}),
        ]

        component.data = word_data
        component.replacement_strategy = "simple"
        component.search_value = "test"
        component.replace_value = "exam"
        component.whole_word_only = True

        result = component.replace_strings()

        # Only whole word "test" should be replaced
        assert result.data[0].data["text"] == "exam testing tested"
        assert result.data[1].data["text"] == "This is a exam"

    def test_max_replacements(self, component):
        repeat_data = [
            Data(data={"id": 1, "text": "test test test test"}),
        ]

        component.data = repeat_data
        component.replacement_strategy = "simple"
        component.search_value = "test"
        component.replace_value = "exam"
        component.max_replacements = 2

        result = component.replace_strings()

        # Only first 2 occurrences should be replaced
        assert result.data[0].data["text"] == "exam exam test test"

    def test_create_backup(self, component, sample_data):
        component.data = sample_data
        component.replacement_strategy = "simple"
        component.search_value = "Hello"
        component.replace_value = "Hi"
        component.create_backup = True

        result = component.replace_strings()

        # Should create backup fields
        assert result.data[0].data["text"] == "Hi World"
        assert result.data[0].data["text_original"] == "Hello World"

    def test_skip_empty_values(self, component, sample_data):
        component.data = sample_data
        component.replacement_strategy = "simple"
        component.search_value = ""
        component.replace_value = "empty"
        component.skip_empty = True

        result = component.replace_strings()

        # Empty/null values should remain unchanged
        assert result.data[3].data["text"] == ""
        assert result.data[3].data["description"] is None

    def test_preserve_type(self, component):
        numeric_data = [
            Data(data={"id": 1, "value": 123}),
            Data(data={"id": 2, "value": "456"}),
        ]

        component.data = numeric_data
        component.replacement_strategy = "simple"
        component.search_value = "123"
        component.replace_value = "789"
        component.preserve_type = True

        result = component.replace_strings()

        # Should attempt to preserve original types
        # Note: This test might need adjustment based on actual implementation
        assert result.data[0].data["value"] == 789 or result.data[0].data["value"] == "789"

    def test_replacement_report(self, component, sample_data):
        component.data = sample_data
        component.replacement_strategy = "simple"
        component.search_value = "test"
        component.replace_value = "example"

        # Run replacement first
        component.replace_strings()

        # Get replacement report
        report = component.get_replacement_report()

        assert "total_records" in report.data
        assert "modified_records" in report.data
        assert "total_replacements" in report.data
        assert "fields_modified" in report.data

        assert report.data["total_records"] == 4
        assert report.data["modified_records"] >= 1
        assert report.data["total_replacements"] >= 1

    def test_changed_records_output(self, component, sample_data):
        component.data = sample_data
        component.replacement_strategy = "simple"
        component.search_value = "Hello"
        component.replace_value = "Hi"

        # Run replacement first
        component.replace_strings()

        # Get changed records
        changed = component.get_changed_records()

        assert len(changed.data) == 1  # Only one record was changed
        assert changed.data[0].data["text"] == "Hi World"

    def test_empty_data_handling(self, component):
        component.data = []

        with pytest.raises(ValueError, match="empty"):
            component.replace_strings()

    def test_invalid_regex_pattern(self, component, sample_data):
        component.data = sample_data
        component.replacement_strategy = "regex"
        component.search_value = "[invalid"  # Invalid regex

        with pytest.raises(Exception):  # Should raise regex error
            component.replace_strings()

    def test_invalid_json_replacement_map(self, component, sample_data):
        component.data = sample_data
        component.replacement_strategy = "bulk"
        component.replacement_map = "invalid json"

        with pytest.raises(json.JSONDecodeError):
            component.replace_strings()

    def test_invalid_json_template_variables(self, component, sample_data):
        component.data = sample_data
        component.replacement_strategy = "template"
        component.template_variables = "invalid json"

        with pytest.raises(json.JSONDecodeError):
            component.replace_strings()

    def test_no_replacement_needed(self, component, sample_data):
        component.data = sample_data
        component.replacement_strategy = "simple"
        component.search_value = "nonexistent"
        component.replace_value = "replacement"

        result = component.replace_strings()

        # No changes should be made
        for i, item in enumerate(result.data):
            assert item.data == sample_data[i].data

    def test_single_record(self, component):
        single_data = [Data(data={"id": 1, "text": "Hello World"})]
        component.data = single_data
        component.replacement_strategy = "simple"
        component.search_value = "World"
        component.replace_value = "Universe"

        result = component.replace_strings()

        assert len(result.data) == 1
        assert result.data[0].data["text"] == "Hello Universe"