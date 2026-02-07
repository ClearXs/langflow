"""Entity extraction service - Extract entities and relations from text using LLM."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage

if TYPE_CHECKING:
    from langchain_litellm import ChatLiteLLM

    from langflow.services.database.models.entity.schema import EntityCreate

logger = logging.getLogger(__name__)


class EntityExtractionService:
    """Service for extracting entities and relations from text.

    Uses LLM for entity recognition, type classification, and relation extraction.
    """

    # Supported entity types
    ENTITY_TYPES = [
        "Person",  # People
        "Organization",  # Organizations
        "Location",  # Places
        "Event",  # Events
        "Concept",  # Concepts
        "Product",  # Products
        "Technology",  # Technologies
        "Date",  # Dates/Times
        "Other",  # Other types
    ]

    # Supported relation types
    RELATION_TYPES = [
        "PartOf",  # Part-Whole relationship
        "IsA",  # Type relationship
        "LeadsTo",  # Causation
        "RelatedTo",  # General relation
        "LocatedAt",  # Location
        "CreatedBy",  # Creator
        "OccurredAt",  # Occurrence
        "Uses",  # Usage
        "Owns",  # Ownership
        "WorksFor",  # Employment
    ]

    @staticmethod
    def _build_entity_extraction_prompt(text: str, max_entities: int = 20) -> str:
        """Build prompt for entity extraction.

        Args:
            text: Text to extract entities from
            max_entities: Maximum number of entities to extract

        Returns:
            LLM prompt string
        """
        entity_types_str = ", ".join(EntityExtractionService.ENTITY_TYPES)

        return f"""Extract key entities from the following text. For each entity, provide: name, type, brief description, and possible aliases.

**Entity Types**: {entity_types_str}

**Text**:
{text}

**Requirements**:
1. Extract at most {max_entities} most important entities
2. Each entity must have a clear name and type
3. Description should be concise (1-2 sentences)
4. If there are aliases or abbreviations, list them in aliases
5. Only extract entities explicitly mentioned in the text

**Output Format** (strict JSON):
{{
  "entities": [
    {{
      "name": "Entity Name",
      "type": "Entity Type",
      "description": "Brief description",
      "aliases": ["alias1", "alias2"]
    }}
  ]
}}

Return only JSON, do not include any other text."""

    @staticmethod
    def _build_relation_extraction_prompt(
        text: str,
        entities: list[dict],
        max_relations: int = 30,
    ) -> str:
        """Build prompt for relation extraction.

        Args:
            text: Original text
            entities: List of extracted entities
            max_relations: Maximum number of relations to extract

        Returns:
            LLM prompt string
        """
        relation_types_str = ", ".join(EntityExtractionService.RELATION_TYPES)
        entities_str = "\n".join([f"- {e['name']} ({e['type']})" for e in entities])

        return f"""Extract relationships between entities from the text.

**Relation Types**: {relation_types_str}

**Identified Entities**:
{entities_str}

**Original Text**:
{text}

**Requirements**:
1. Only extract relations between the above entities
2. Extract at most {max_relations} relations
3. Each relation must have clear source entity, target entity, and type
4. Description should explain the specific meaning of the relation
5. Weight range 0.0-1.0, indicating importance/confidence of the relation

**Output Format** (strict JSON):
{{
  "relations": [
    {{
      "source": "Source Entity Name",
      "target": "Target Entity Name",
      "type": "Relation Type",
      "description": "Relation description",
      "weight": 0.8
    }}
  ]
}}

Return only JSON, do not include any other text."""

    @staticmethod
    async def extract_entities_from_text(
        text: str,
        llm: ChatLiteLLM,
        space_id: int,
        document_id: int | None = None,
        chunk_id: int | None = None,
        max_entities: int = 20,
    ) -> list[EntityCreate]:
        """Extract entities from text.

        Args:
            text: Text to extract entities from
            llm: ChatLiteLLM instance
            space_id: Space ID
            document_id: Document ID (optional)
            chunk_id: Chunk ID (optional)
            max_entities: Maximum number of entities to extract

        Returns:
            List of EntityCreate objects
        """
        if not text or not text.strip():
            return []

        try:
            # Build prompt
            prompt = EntityExtractionService._build_entity_extraction_prompt(text, max_entities)

            # Call LLM
            messages = [
                SystemMessage(content="You are a professional knowledge graph builder, skilled at extracting entities from text."),
                HumanMessage(content=prompt),
            ]

            response = await llm.agenerate(messages=[messages])
            result_text = response.generations[0][0].text.strip()

            # Parse JSON response
            # Try to extract JSON (some models return in code blocks)
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            entities_data = json.loads(result_text)

            # Convert to EntityCreate objects
            entity_creates = []
            for entity_dict in entities_data.get("entities", []):
                # Validate required fields
                if not entity_dict.get("name") or not entity_dict.get("type"):
                    continue

                entity_create = EntityCreate(
                    space_id=space_id,
                    document_id=document_id,
                    chunk_id=chunk_id,
                    name=entity_dict["name"],
                    entity_type=entity_dict["type"],
                    description=entity_dict.get("description"),
                    aliases=entity_dict.get("aliases", []),
                    properties={},
                )
                entity_creates.append(entity_create)

            logger.info(f"Extracted {len(entity_creates)} entities from text")
            return entity_creates

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse entity extraction result: {e}\nResponse content: {result_text}")
            return []
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []

    @staticmethod
    async def extract_relations_from_text(
        text: str,
        entities: list[dict],
        llm: ChatLiteLLM,
        space_id: int,
        document_id: int | None = None,
        chunk_id: int | None = None,
        max_relations: int = 30,
    ) -> list[dict]:
        """Extract relations between entities from text.

        Note: This method returns a list of dicts, entity names need to be mapped to entity IDs after calling.

        Args:
            text: Original text
            entities: List of extracted entities (dict format, with name, type, etc.)
            llm: ChatLiteLLM instance
            space_id: Space ID
            document_id: Document ID (optional)
            chunk_id: Chunk ID (optional)
            max_relations: Maximum number of relations to extract

        Returns:
            List of relation dicts (containing source, target, type, description, weight)
        """
        if not text or not entities:
            return []

        try:
            # Build prompt
            prompt = EntityExtractionService._build_relation_extraction_prompt(
                text, entities, max_relations
            )

            # Call LLM
            messages = [
                SystemMessage(content="You are a professional knowledge graph builder, skilled at identifying relationships between entities."),
                HumanMessage(content=prompt),
            ]

            response = await llm.agenerate(messages=[messages])
            result_text = response.generations[0][0].text.strip()

            # Parse JSON response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            relations_data = json.loads(result_text)

            # Validate and return relations
            valid_relations = []
            for relation_dict in relations_data.get("relations", []):
                # Validate required fields
                if not all(k in relation_dict for k in ["source", "target", "type"]):
                    continue

                # Ensure weight is within valid range
                weight = relation_dict.get("weight", 1.0)
                if not isinstance(weight, (int, float)):
                    weight = 1.0
                weight = max(0.0, min(1.0, float(weight)))

                valid_relation = {
                    "source_name": relation_dict["source"],
                    "target_name": relation_dict["target"],
                    "relation_type": relation_dict["type"],
                    "description": relation_dict.get("description"),
                    "weight": weight,
                    "space_id": space_id,
                    "document_id": document_id,
                    "chunk_id": chunk_id,
                }
                valid_relations.append(valid_relation)

            logger.info(f"Extracted {len(valid_relations)} relations from text")
            return valid_relations

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse relation extraction result: {e}\nResponse content: {result_text}")
            return []
        except Exception as e:
            logger.error(f"Relation extraction failed: {e}")
            return []

    @staticmethod
    def merge_similar_entities(entities: list[EntityCreate]) -> list[EntityCreate]:
        """Merge similar entities (based on name similarity).

        Args:
            entities: List of EntityCreate objects

        Returns:
            Deduplicated list of EntityCreate objects
        """
        if not entities:
            return []

        # Simple name-based deduplication
        # TODO: Implement more sophisticated similarity calculation (using embedding)
        unique_entities = {}

        for entity in entities:
            # Normalize name (lowercase, strip whitespace)
            normalized_name = entity.name.lower().strip()

            if normalized_name not in unique_entities:
                unique_entities[normalized_name] = entity
            else:
                # If entity already exists, merge aliases
                existing = unique_entities[normalized_name]
                existing.aliases = list(set(existing.aliases + entity.aliases + [entity.name]))

        logger.info(f"After deduplication: {len(unique_entities)} unique entities (original: {len(entities)})")
        return list(unique_entities.values())
