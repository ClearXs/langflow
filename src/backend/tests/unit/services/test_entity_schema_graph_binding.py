from langflow.services.database.models.entity.schema import EntityCreate, EntityRead, EntityUpdate
from langflow.services.database.models.relation.schema import RelationCreate, RelationRead, RelationUpdate


def test_entity_schema_graph_node_id_field():
    assert "graph_node_id" in EntityCreate.model_fields
    assert "graph_node_id" in EntityRead.model_fields
    assert "graph_node_id" in EntityUpdate.model_fields
    assert "embedding" not in EntityCreate.model_fields
    assert "embedding" not in EntityRead.model_fields
    assert "embedding" not in EntityUpdate.model_fields


def test_relation_schema_graph_edge_id_field():
    assert "graph_edge_id" in RelationCreate.model_fields
    assert "graph_edge_id" in RelationRead.model_fields
    assert "graph_edge_id" in RelationUpdate.model_fields
