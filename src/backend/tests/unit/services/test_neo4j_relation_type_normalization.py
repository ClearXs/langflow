from langflow.services.graph.neo4j_service import Neo4jGraphService


def test_normalize_relation_type():
    service = Neo4jGraphService()
    assert service._normalize_relation_type("Part Of") == "Part_Of"
    assert service._normalize_relation_type("") == "RELATED_TO"
    assert service._normalize_relation_type("Works-For") == "Works_For"
