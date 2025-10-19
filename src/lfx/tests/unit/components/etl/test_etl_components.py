"""Unit tests for ETL components."""

from lfx.components.input_output import (
    ETLAPIInputComponent,
    ETLCSVOutputComponent,
    ETLExcelOutputComponent,
    ETLFileInputComponent,
    ETLTableInputComponent,
    ETLTableOutputComponent,
)
from lfx.components.manipulations import (
    ETLDataCleaningComponent,
    ETLFieldNameMappingComponent,
)
from lfx.components.operations import (
    ETLDeduplicationComponent,
    ETLDualStreamJoinComponent,
    ETLGroupByComponent,
    ETLMultiStreamUnionComponent,
)
from lfx.components.scripts import (
    ETLPythonScriptComponent,
    ETLShellScriptComponent,
)
from lfx.components.security import ETLDataMaskingComponent


class TestETLInputComponents:
    """Test ETL input components."""

    def test_table_input_creation(self):
        """Test creating ETL table input component."""
        component = ETLTableInputComponent()
        assert component.display_name is not None
        assert component.name == "ETLTableInput"

    def test_file_input_creation(self):
        """Test creating ETL file input component."""
        component = ETLFileInputComponent()
        assert component.display_name is not None
        assert component.name == "ETLFileInput"

    def test_api_input_creation(self):
        """Test creating ETL API input component."""
        component = ETLAPIInputComponent()
        assert component.display_name is not None
        assert component.name == "ETLAPIInput"


class TestETLOperationComponents:
    """Test ETL operation components."""

    def test_join_component_creation(self):
        """Test creating dual stream join component."""
        component = ETLDualStreamJoinComponent()
        assert component.display_name is not None
        assert component.name == "ETLDualStreamJoin"

    def test_union_component_creation(self):
        """Test creating multi stream union component."""
        component = ETLMultiStreamUnionComponent()
        assert component.display_name is not None
        assert component.name == "ETLMultiStreamUnion"

    def test_group_by_component_creation(self):
        """Test creating group by component."""
        component = ETLGroupByComponent()
        assert component.display_name is not None
        assert component.name == "ETLGroupBy"

    def test_deduplication_component_creation(self):
        """Test creating deduplication component."""
        component = ETLDeduplicationComponent()
        assert component.display_name is not None
        assert component.name == "ETLDeduplication"


class TestETLManipulationComponents:
    """Test ETL manipulation components."""

    def test_field_mapping_creation(self):
        """Test creating field name mapping component."""
        component = ETLFieldNameMappingComponent()
        assert component.display_name is not None
        assert component.name == "ETLFieldNameMapping"

    def test_data_cleaning_creation(self):
        """Test creating data cleaning component."""
        component = ETLDataCleaningComponent()
        assert component.display_name is not None
        assert component.name == "ETLDataCleaning"


class TestETLSecurityComponents:
    """Test ETL security components."""

    def test_masking_component_creation(self):
        """Test creating data masking component."""
        component = ETLDataMaskingComponent()
        assert component.display_name is not None
        assert component.name == "ETLDataMasking"


class TestETLOutputComponents:
    """Test ETL output components."""

    def test_table_output_creation(self):
        """Test creating table output component."""
        component = ETLTableOutputComponent()
        assert component.display_name is not None
        assert component.name == "ETLTableOutput"

    def test_excel_output_creation(self):
        """Test creating Excel output component."""
        component = ETLExcelOutputComponent()
        assert component.display_name is not None
        assert component.name == "ETLExcelOutput"

    def test_csv_output_creation(self):
        """Test creating CSV output component."""
        component = ETLCSVOutputComponent()
        assert component.display_name is not None
        assert component.name == "ETLCSVOutput"


class TestETLScriptComponents:
    """Test ETL script components."""

    def test_shell_script_creation(self):
        """Test creating shell script component."""
        component = ETLShellScriptComponent()
        assert component.display_name is not None
        assert component.name == "ETLShellScript"

    def test_python_script_creation(self):
        """Test creating Python script component."""
        component = ETLPythonScriptComponent()
        assert component.display_name is not None
        assert component.name == "ETLPythonScript"
