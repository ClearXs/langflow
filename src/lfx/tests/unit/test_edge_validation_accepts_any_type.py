"""Test edge validation with accepts_any_type attribute."""

import pytest

from lfx.custom.custom_component.component import Component
from lfx.graph.edge.base import Edge
from lfx.graph.edge.schema import EdgeData
from lfx.graph.vertex.base import Vertex
from lfx.inputs.inputs import HandleInput
from lfx.template.field.base import Output


class TestEdgeValidationAcceptsAnyType:
    """Test that edges with accepts_any_type=True skip type validation."""

    def test_edge_validation_skips_with_accepts_any_type(self):
        """Test that edge validation succeeds when target input has accepts_any_type=True."""

        # Create a source component with Data output
        class SourceComponent(Component):
            display_name = "Source"
            outputs = [Output(name="data_output", method="run")]

            def run(self):
                return {"result": "data"}

        # Create a target component with universal input (accepts_any_type=True)
        class TargetComponent(Component):
            display_name = "Target"
            include_universal_input = True  # This adds upstream_data with accepts_any_type=True

            inputs = []
            outputs = [Output(name="result", method="process")]

            def process(self):
                return "processed"

        # Create component instances
        source_comp = SourceComponent()
        target_comp = TargetComponent()

        # Verify target has upstream_data with accepts_any_type=True
        assert "upstream_data" in target_comp._inputs
        assert target_comp._inputs["upstream_data"].accepts_any_type is True

        # Create mock vertices
        class MockVertex:
            def __init__(self, component, vertex_id, template_data=None):
                self.id = vertex_id
                self.display_name = component.display_name
                self.vertex_type = component.display_name
                self.custom_component = component
                # Mock outputs format
                self.outputs = [{"name": "data_output", "types": ["Data"]}]
                self.required_inputs = []
                self.optional_inputs = []
                # Mock data structure with template
                self.data = {"node": {"template": template_data or {}}}

        # Create target template with accepts_any_type=True
        target_template = {
            "upstream_data": {
                "name": "upstream_data",
                "display_name": "Hook",
                "input_types": [],
                "accepts_any_type": True,  # This is the key attribute
                "required": False,
                "show": True,
            }
        }

        source_vertex = MockVertex(source_comp, "source-123")
        target_vertex = MockVertex(target_comp, "target-456", target_template)

        # Create edge data connecting source to target's upstream_data
        edge_data: EdgeData = {
            "source": "source-123",
            "target": "target-456",
            "data": {
                "sourceHandle": {
                    "dataType": "Source",
                    "id": "source-123|data_output",
                    "name": "data_output",
                    "output_types": ["Data"],
                },
                "targetHandle": {
                    "fieldName": "upstream_data",
                    "id": "target-456|upstream_data",
                    "inputTypes": [],  # Empty list = accept any type
                    "type": "Data",
                },
            },
        }

        # Create edge and validate
        edge = Edge(source_vertex, target_vertex, edge_data)

        # Edge should be valid because accepts_any_type=True
        assert edge.valid is True
        assert edge.matched_type == "Data"

    def test_edge_validation_normal_without_accepts_any_type(self):
        """Test that normal edge validation still works for inputs without accepts_any_type."""

        # Create a source component
        class SourceComponent(Component):
            display_name = "Source"
            outputs = [Output(name="text_output", method="run")]

            def run(self):
                return "text"

        # Create a target component with specific input type
        class TargetComponent(Component):
            display_name = "Target"

            inputs = [
                HandleInput(
                    name="text_input",
                    display_name="Text Input",
                    input_types=["Message"],  # Specific type requirement
                    required=True,
                )
            ]
            outputs = [Output(name="result", method="process")]

            def process(self):
                return "processed"

        # Create component instances
        source_comp = SourceComponent()
        target_comp = TargetComponent()

        # Verify text_input does NOT have accepts_any_type
        assert "text_input" in target_comp._inputs
        assert target_comp._inputs["text_input"].accepts_any_type is False

        # Create mock vertices
        class MockVertex:
            def __init__(self, component, vertex_id, template_data=None):
                self.id = vertex_id
                self.display_name = component.display_name
                self.vertex_type = component.display_name
                self.custom_component = component
                # Mock outputs format
                self.outputs = [{"name": "text_output", "types": ["Message"]}]
                self.required_inputs = ["Message"]
                self.optional_inputs = []
                # Mock data structure with template
                self.data = {"node": {"template": template_data or {}}}

        # Create target template without accepts_any_type
        target_template = {
            "text_input": {
                "name": "text_input",
                "display_name": "Text Input",
                "input_types": ["Message"],
                "accepts_any_type": False,  # Normal input with specific type
                "required": True,
            }
        }

        source_vertex = MockVertex(source_comp, "source-789")
        target_vertex = MockVertex(target_comp, "target-012", target_template)

        # Create edge data
        edge_data: EdgeData = {
            "source": "source-789",
            "target": "target-012",
            "data": {
                "sourceHandle": {
                    "dataType": "Source",
                    "id": "source-789|text_output",
                    "name": "text_output",
                    "output_types": ["Message"],
                },
                "targetHandle": {
                    "fieldName": "text_input",
                    "id": "target-012|text_input",
                    "inputTypes": ["Message"],
                    "type": "Message",
                },
            },
        }

        # Create edge and validate - should use normal validation path
        edge = Edge(source_vertex, target_vertex, edge_data)

        # Edge should be valid because types match
        assert edge.valid is True
        assert edge.matched_type == "Message"

    def test_edge_validation_fails_without_type_match(self):
        """Test that edge validation fails when types don't match and accepts_any_type=False."""

        # Create a source component with incompatible output type
        class SourceComponent(Component):
            display_name = "Source"
            outputs = [Output(name="number_output", method="run")]

            def run(self):
                return 42

        # Create a target component expecting different type
        class TargetComponent(Component):
            display_name = "Target"

            inputs = [
                HandleInput(
                    name="text_input",
                    display_name="Text Input",
                    input_types=["Message"],  # Expects Message
                    required=True,
                )
            ]
            outputs = [Output(name="result", method="process")]

            def process(self):
                return "processed"

        # Create component instances
        source_comp = SourceComponent()
        target_comp = TargetComponent()

        # Create mock vertices
        class MockVertex:
            def __init__(self, component, vertex_id, template_data=None):
                self.id = vertex_id
                self.display_name = component.display_name
                self.vertex_type = component.display_name
                self.custom_component = component
                # Mock outputs format - incompatible type
                self.outputs = [{"name": "number_output", "types": ["Number"]}]
                self.required_inputs = ["Message"]
                self.optional_inputs = []
                # Mock data structure with template
                self.data = {"node": {"template": template_data or {}}}

        # Create target template without accepts_any_type
        target_template = {
            "text_input": {
                "name": "text_input",
                "display_name": "Text Input",
                "input_types": ["Message"],
                "accepts_any_type": False,  # Normal input with specific type
                "required": True,
            }
        }

        source_vertex = MockVertex(source_comp, "source-345")
        target_vertex = MockVertex(target_comp, "target-678", target_template)

        # Create edge data with mismatched types
        edge_data: EdgeData = {
            "source": "source-345",
            "target": "target-678",
            "data": {
                "sourceHandle": {
                    "dataType": "Source",
                    "id": "source-345|number_output",
                    "name": "number_output",
                    "output_types": ["Number"],
                },
                "targetHandle": {
                    "fieldName": "text_input",
                    "id": "target-678|text_input",
                    "inputTypes": ["Message"],
                    "type": "Message",
                },
            },
        }

        # Edge creation should fail due to type mismatch
        # Note: Fails at handle validation first with "invalid handles"
        with pytest.raises(ValueError, match="invalid handles|has no matched type"):
            Edge(source_vertex, target_vertex, edge_data)
