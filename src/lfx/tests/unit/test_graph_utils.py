"""Unit tests for graph_utils module."""

import pytest

from lfx.custom.graph_utils import find_upstream_node_id


class TestFindUpstreamNodeId:
    """Test suite for find_upstream_node_id function."""

    def test_langflow_format_with_nested_fieldname(self):
        """Test finding upstream node with Langflow nested format."""
        graph_data = {
            "nodes": [],
            "edges": [
                {
                    "source": "ETLTableInput-p1qpP",
                    "target": "ETLFieldNameMapping-y1UeC",
                    "data": {
                        "targetHandle": {
                            "fieldName": "data_input",
                            "id": "ETLFieldNameMapping-y1UeC",
                            "inputTypes": ["Data"],
                            "type": "other",
                        },
                        "sourceHandle": {
                            "dataType": "ETLTableInput",
                            "id": "ETLTableInput-p1qpP",
                            "name": "data",
                            "output_types": ["Data"],
                        },
                    },
                }
            ],
        }

        result = find_upstream_node_id(graph_data, "ETLFieldNameMapping-y1UeC", "data_input")

        assert result == "ETLTableInput-p1qpP"

    def test_react_flow_format_with_simple_string(self):
        """Test finding upstream node with React Flow simple string format."""
        graph_data = {
            "nodes": [],
            "edges": [
                {
                    "source": "node1",
                    "target": "node2",
                    "targetHandle": "data_input",
                    "sourceHandle": "output",
                }
            ],
        }

        result = find_upstream_node_id(graph_data, "node2", "data_input")

        assert result == "node1"

    def test_no_edges_returns_none(self):
        """Test that function returns None when no edges exist."""
        graph_data = {"nodes": []}

        result = find_upstream_node_id(graph_data, "node1", "input1")

        assert result is None

    def test_no_matching_edge_returns_none(self):
        """Test that function returns None when no edge matches."""
        graph_data = {
            "nodes": [],
            "edges": [
                {
                    "source": "node1",
                    "target": "node2",
                    "targetHandle": "other_input",
                }
            ],
        }

        result = find_upstream_node_id(graph_data, "node2", "data_input")

        assert result is None

    def test_wrong_target_node_returns_none(self):
        """Test that function returns None when target node doesn't match."""
        graph_data = {
            "nodes": [],
            "edges": [
                {
                    "source": "node1",
                    "target": "node2",
                    "targetHandle": "data_input",
                }
            ],
        }

        result = find_upstream_node_id(graph_data, "node3", "data_input")

        assert result is None

    def test_multiple_edges_finds_correct_one(self):
        """Test finding correct edge when multiple edges exist."""
        graph_data = {
            "nodes": [],
            "edges": [
                {
                    "source": "node1",
                    "target": "node2",
                    "targetHandle": "input1",
                },
                {
                    "source": "node3",
                    "target": "node2",
                    "data": {
                        "targetHandle": {
                            "fieldName": "input2",
                        }
                    },
                },
                {
                    "source": "node4",
                    "target": "node5",
                    "targetHandle": "input2",
                },
            ],
        }

        # Should find node3 for input2
        result = find_upstream_node_id(graph_data, "node2", "input2")
        assert result == "node3"

        # Should find node1 for input1
        result = find_upstream_node_id(graph_data, "node2", "input1")
        assert result == "node1"

    def test_ignore_json_string_in_target_handle(self):
        """Test that JSON strings in targetHandle are ignored."""
        graph_data = {
            "nodes": [],
            "edges": [
                {
                    "source": "ETLTableInput-p1qpP",
                    "sourceHandle": '{"dataType":"ETLTableInput"}',  # JSON string - should be ignored
                    "target": "ETLFieldNameMapping-y1UeC",
                    "targetHandle": '{"fieldName":"data_input"}',  # JSON string - should be ignored
                    "data": {
                        "targetHandle": {
                            "fieldName": "data_input",  # This should be used instead
                        }
                    },
                }
            ],
        }

        result = find_upstream_node_id(graph_data, "ETLFieldNameMapping-y1UeC", "data_input")

        assert result == "ETLTableInput-p1qpP"

    def test_prefer_nested_over_top_level(self):
        """Test that nested format is preferred over top-level."""
        graph_data = {
            "nodes": [],
            "edges": [
                {
                    "source": "node1",
                    "target": "node2",
                    "targetHandle": "wrong_input",  # This should be ignored
                    "data": {
                        "targetHandle": {
                            "fieldName": "correct_input",  # This should be used
                        }
                    },
                }
            ],
        }

        # Should use nested format
        result = find_upstream_node_id(graph_data, "node2", "correct_input")
        assert result == "node1"

        # Should not match wrong_input
        result = find_upstream_node_id(graph_data, "node2", "wrong_input")
        assert result is None

    def test_fallback_to_top_level_when_nested_missing(self):
        """Test fallback to top-level when nested format is not available."""
        graph_data = {
            "nodes": [],
            "edges": [
                {
                    "source": "node1",
                    "target": "node2",
                    "targetHandle": "data_input",
                    # No nested data.targetHandle
                }
            ],
        }

        result = find_upstream_node_id(graph_data, "node2", "data_input")

        assert result == "node1"
