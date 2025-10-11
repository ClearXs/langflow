from __future__ import annotations
import os

import i18n
import json
import uuid
from typing import Any

from opensearchpy import OpenSearch, helpers

from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.base.vectorstores.vector_store_connection_decorator import vector_store_connection
from lfx.io import BoolInput, DropdownInput, HandleInput, IntInput, MultilineInput, SecretStrInput, StrInput, TableInput
from lfx.log import logger
from lfx.schema.data import Data


@vector_store_connection
class OpenSearchVectorStoreComponent(LCVectorStoreComponent):
    """OpenSearch Vector Store Component with Hybrid Search Capabilities.

    This component provides vector storage and retrieval using OpenSearch, combining semantic
    similarity search (KNN) with keyword-based search for optimal results. It supports document
    ingestion, vector embeddings, and advanced filtering with authentication options.

    Features:
    - Vector storage with configurable engines (jvector, nmslib, faiss, lucene)
    - Hybrid search combining KNN vector similarity and keyword matching
    - Flexible authentication (Basic auth, JWT tokens)
    - Advanced filtering and aggregations
    - Metadata injection during document ingestion
    """

    display_name: str = "OpenSearch"
    icon: str = "OpenSearch"
    description: str = i18n.t('components.elastic.opensearch.description')

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    # Keys we consider baseline
    default_keys: list[str] = [
        "opensearch_url",
        "index_name",
        *[i.name for i in LCVectorStoreComponent.inputs],
        "embedding",
        "vector_field",
        "number_of_results",
        "auth_mode",
        "username",
        "password",
        "jwt_token",
        "jwt_header",
        "bearer_prefix",
        "use_ssl",
        "verify_certs",
        "filter_expression",
        "engine",
        "space_type",
        "ef_construction",
        "m",
        "docs_metadata",
    ]

    inputs = [
        TableInput(
            trigger_text=i18n.t(
                'components.inputs.input_mixin.open_table'),
            name="docs_metadata",
            display_name=i18n.t(
                'components.elastic.opensearch.docs_metadata.display_name'),
            info=i18n.t('components.elastic.opensearch.docs_metadata.info'),
            table_schema=[
                {
                    "name": "key",
                    "display_name": i18n.t('components.elastic.opensearch.docs_metadata.schema.key'),
                    "type": "str",
                    "description": i18n.t('components.elastic.opensearch.docs_metadata.schema.key_desc'),
                },
                {
                    "name": "value",
                    "display_name": i18n.t('components.elastic.opensearch.docs_metadata.schema.value'),
                    "type": "str",
                    "description": i18n.t('components.elastic.opensearch.docs_metadata.schema.value_desc'),
                },
            ],
            value=[],
            input_types=["Data"],
        ),
        StrInput(
            name="opensearch_url",
            display_name=i18n.t(
                'components.elastic.opensearch.opensearch_url.display_name'),
            value="http://localhost:9200",
            info=i18n.t('components.elastic.opensearch.opensearch_url.info'),
        ),
        StrInput(
            name="index_name",
            display_name=i18n.t(
                'components.elastic.opensearch.index_name.display_name'),
            value="langflow",
            info=i18n.t('components.elastic.opensearch.index_name.info'),
        ),
        DropdownInput(
            name="engine",
            display_name=i18n.t(
                'components.elastic.opensearch.engine.display_name'),
            options=["jvector", "nmslib", "faiss", "lucene"],
            value="jvector",
            info=i18n.t('components.elastic.opensearch.engine.info'),
            advanced=True,
        ),
        DropdownInput(
            name="space_type",
            display_name=i18n.t(
                'components.elastic.opensearch.space_type.display_name'),
            options=["l2", "l1", "cosinesimil", "linf", "innerproduct"],
            value="l2",
            info=i18n.t('components.elastic.opensearch.space_type.info'),
            advanced=True,
        ),
        IntInput(
            name="ef_construction",
            display_name=i18n.t(
                'components.elastic.opensearch.ef_construction.display_name'),
            value=512,
            info=i18n.t('components.elastic.opensearch.ef_construction.info'),
            advanced=True,
        ),
        IntInput(
            name="m",
            display_name=i18n.t(
                'components.elastic.opensearch.m.display_name'),
            value=16,
            info=i18n.t('components.elastic.opensearch.m.info'),
            advanced=True,
        ),
        *LCVectorStoreComponent.inputs,
        HandleInput(
            name="embedding",
            display_name=i18n.t(
                'components.elastic.opensearch.embedding.display_name'),
            input_types=["Embeddings"]
        ),
        StrInput(
            name="vector_field",
            display_name=i18n.t(
                'components.elastic.opensearch.vector_field.display_name'),
            value="chunk_embedding",
            advanced=True,
            info=i18n.t('components.elastic.opensearch.vector_field.info'),
        ),
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.elastic.opensearch.number_of_results.display_name'),
            value=10,
            advanced=True,
            info=i18n.t(
                'components.elastic.opensearch.number_of_results.info'),
        ),
        MultilineInput(
            name="filter_expression",
            display_name=i18n.t(
                'components.elastic.opensearch.filter_expression.display_name'),
            value="",
            info=i18n.t(
                'components.elastic.opensearch.filter_expression.info'),
        ),
        DropdownInput(
            name="auth_mode",
            display_name=i18n.t(
                'components.elastic.opensearch.auth_mode.display_name'),
            value="basic",
            options=["basic", "jwt"],
            info=i18n.t('components.elastic.opensearch.auth_mode.info'),
            real_time_refresh=True,
            advanced=False,
        ),
        StrInput(
            name="username",
            display_name=i18n.t(
                'components.elastic.opensearch.username.display_name'),
            value="admin",
            show=False,
        ),
        SecretStrInput(
            name="password",
            display_name=i18n.t(
                'components.elastic.opensearch.password.display_name'),
            value="admin",
            show=False,
        ),
        SecretStrInput(
            name="jwt_token",
            display_name=i18n.t(
                'components.elastic.opensearch.jwt_token.display_name'),
            value="JWT",
            load_from_db=False,
            show=True,
            info=i18n.t('components.elastic.opensearch.jwt_token.info'),
        ),
        StrInput(
            name="jwt_header",
            display_name=i18n.t(
                'components.elastic.opensearch.jwt_header.display_name'),
            value="Authorization",
            show=False,
            advanced=True,
        ),
        BoolInput(
            name="bearer_prefix",
            display_name=i18n.t(
                'components.elastic.opensearch.bearer_prefix.display_name'),
            value=True,
            show=False,
            advanced=True,
        ),
        BoolInput(
            name="use_ssl",
            display_name=i18n.t(
                'components.elastic.opensearch.use_ssl.display_name'),
            value=True,
            advanced=True,
            info=i18n.t('components.elastic.opensearch.use_ssl.info'),
        ),
        BoolInput(
            name="verify_certs",
            display_name=i18n.t(
                'components.elastic.opensearch.verify_certs.display_name'),
            value=False,
            advanced=True,
            info=i18n.t('components.elastic.opensearch.verify_certs.info'),
        ),
    ]

    def _default_text_mapping(
        self,
        dim: int,
        engine: str = "jvector",
        space_type: str = "l2",
        ef_search: int = 512,
        ef_construction: int = 100,
        m: int = 16,
        vector_field: str = "vector_field",
    ) -> dict[str, Any]:
        """Create the default OpenSearch index mapping for vector search."""
        logger.debug(i18n.t('components.elastic.opensearch.logs.creating_index_mapping',
                            dim=dim, engine=engine, space_type=space_type))
        return {
            "settings": {"index": {"knn": True, "knn.algo_param.ef_search": ef_search}},
            "mappings": {
                "properties": {
                    vector_field: {
                        "type": "knn_vector",
                        "dimension": dim,
                        "method": {
                            "name": "disk_ann",
                            "space_type": space_type,
                            "engine": engine,
                            "parameters": {"ef_construction": ef_construction, "m": m},
                        },
                    }
                }
            },
        }

    def _validate_aoss_with_engines(self, *, is_aoss: bool, engine: str) -> None:
        """Validate engine compatibility with Amazon OpenSearch Serverless."""
        if is_aoss and engine not in {"nmslib", "faiss"}:
            error_msg = i18n.t(
                'components.elastic.opensearch.errors.aoss_engine_incompatible')
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _is_aoss_enabled(self, http_auth: Any) -> bool:
        """Determine if Amazon OpenSearch Serverless is being used."""
        is_aoss = http_auth is not None and hasattr(
            http_auth, "service") and http_auth.service == "aoss"
        if is_aoss:
            logger.debug(
                i18n.t('components.elastic.opensearch.logs.aoss_detected'))
        return is_aoss

    def _bulk_ingest_embeddings(
        self,
        client: OpenSearch,
        index_name: str,
        embeddings: list[list[float]],
        texts: list[str],
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None,
        vector_field: str = "vector_field",
        text_field: str = "text",
        mapping: dict | None = None,
        max_chunk_bytes: int | None = 1 * 1024 * 1024,
        *,
        is_aoss: bool = False,
    ) -> list[str]:
        """Efficiently ingest multiple documents with embeddings into OpenSearch."""
        if not mapping:
            mapping = {}

        logger.info(i18n.t('components.elastic.opensearch.logs.preparing_bulk_ingest',
                           count=len(texts)))

        requests = []
        return_ids = []

        for i, text in enumerate(texts):
            metadata = metadatas[i] if metadatas else {}
            _id = ids[i] if ids else str(uuid.uuid4())
            request = {
                "_op_type": "index",
                "_index": index_name,
                vector_field: embeddings[i],
                text_field: text,
                **metadata,
            }
            if is_aoss:
                request["id"] = _id
            else:
                request["_id"] = _id
            requests.append(request)
            return_ids.append(_id)

        if metadatas:
            logger.debug(i18n.t('components.elastic.opensearch.logs.sample_metadata',
                                metadata=str(metadatas[0] if metadatas else {})))
            self.log(f"Sample metadata: {metadatas[0] if metadatas else {}}")

        helpers.bulk(client, requests, max_chunk_bytes=max_chunk_bytes)
        logger.info(i18n.t('components.elastic.opensearch.logs.bulk_ingest_completed',
                           count=len(return_ids)))
        return return_ids

    def _build_auth_kwargs(self) -> dict[str, Any]:
        """Build authentication configuration for OpenSearch client."""
        mode = (self.auth_mode or "basic").strip().lower()
        logger.debug(i18n.t('components.elastic.opensearch.logs.building_auth',
                            mode=mode))

        if mode == "jwt":
            token = (self.jwt_token or "").strip()
            if not token:
                error_msg = i18n.t(
                    'components.elastic.opensearch.errors.jwt_token_missing')
                logger.error(error_msg)
                raise ValueError(error_msg)
            header_name = (self.jwt_header or "Authorization").strip()
            header_value = f"Bearer {token}" if self.bearer_prefix else token
            logger.debug(
                i18n.t('components.elastic.opensearch.logs.jwt_auth_configured'))
            return {"headers": {header_name: header_value}}

        user = (self.username or "").strip()
        pwd = (self.password or "").strip()
        if not user or not pwd:
            error_msg = i18n.t(
                'components.elastic.opensearch.errors.basic_auth_missing')
            logger.error(error_msg)
            raise ValueError(error_msg)
        logger.debug(
            i18n.t('components.elastic.opensearch.logs.basic_auth_configured'))
        return {"http_auth": (user, pwd)}

    def build_client(self) -> OpenSearch:
        """Create and configure an OpenSearch client instance."""
        logger.info(i18n.t('components.elastic.opensearch.logs.building_client',
                           url=self.opensearch_url))
        auth_kwargs = self._build_auth_kwargs()
        client = OpenSearch(
            hosts=[self.opensearch_url],
            use_ssl=self.use_ssl,
            verify_certs=self.verify_certs,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
            **auth_kwargs,
        )
        logger.info(i18n.t('components.elastic.opensearch.logs.client_created'))
        return client

    @check_cached_vector_store
    def build_vector_store(self) -> OpenSearch:
        logger.info(
            i18n.t('components.elastic.opensearch.logs.building_vector_store'))
        self.log(self.ingest_data)
        client = self.build_client()
        self._add_documents_to_vector_store(client=client)
        return client

    def _add_documents_to_vector_store(self, client: OpenSearch) -> None:
        """Process and ingest documents into the OpenSearch vector store."""
        self.ingest_data = self._prepare_ingest_data()

        docs = self.ingest_data or []
        if not docs:
            log_msg = i18n.t(
                'components.elastic.opensearch.logs.no_documents_to_ingest')
            logger.info(log_msg)
            self.log(log_msg)
            return

        logger.info(i18n.t('components.elastic.opensearch.logs.processing_documents',
                           count=len(docs)))

        # Extract texts and metadata from documents
        texts = []
        metadatas = []
        additional_metadata = {}
        if hasattr(self, "docs_metadata") and self.docs_metadata:
            logger.debug(f"[LF] Docs metadata {self.docs_metadata}")
            if isinstance(self.docs_metadata[-1], Data):
                logger.debug(
                    f"[LF] Docs metadata is a Data object {self.docs_metadata}")
                self.docs_metadata = self.docs_metadata[-1].data
                logger.debug(
                    f"[LF] Docs metadata is a Data object {self.docs_metadata}")
                additional_metadata.update(self.docs_metadata)
            else:
                for item in self.docs_metadata:
                    if isinstance(item, dict) and "key" in item and "value" in item:
                        additional_metadata[item["key"]] = item["value"]
        # Replace string "None" values with actual None
        for key, value in additional_metadata.items():
            if value == "None":
                additional_metadata[key] = None
        logger.debug(f"[LF] Additional metadata {additional_metadata}")
        for doc_obj in docs:
            data_copy = json.loads(doc_obj.model_dump_json())
            text = data_copy.pop(doc_obj.text_key, doc_obj.default_value)
            texts.append(text)
            data_copy.update(additional_metadata)
            metadatas.append(data_copy)

        self.log(metadatas)

        if not self.embedding:
            error_msg = i18n.t(
                'components.elastic.opensearch.errors.embedding_required')
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(i18n.t('components.elastic.opensearch.logs.generating_embeddings',
                           count=len(texts)))
        vectors = self.embedding.embed_documents(texts)

        if not vectors:
            log_msg = i18n.t(
                'components.elastic.opensearch.logs.no_vectors_generated')
            logger.warning(log_msg)
            self.log(log_msg)
            return

        dim = len(vectors[0]) if vectors else 768
        logger.debug(i18n.t('components.elastic.opensearch.logs.vector_dimension',
                            dim=dim))

        auth_kwargs = self._build_auth_kwargs()
        is_aoss = self._is_aoss_enabled(auth_kwargs.get("http_auth"))

        engine = getattr(self, "engine", "jvector")
        self._validate_aoss_with_engines(is_aoss=is_aoss, engine=engine)

        space_type = getattr(self, "space_type", "l2")
        ef_construction = getattr(self, "ef_construction", 512)
        m = getattr(self, "m", 16)

        mapping = self._default_text_mapping(
            dim=dim,
            engine=engine,
            space_type=space_type,
            ef_construction=ef_construction,
            m=m,
            vector_field=self.vector_field,
        )

        log_msg = i18n.t('components.elastic.opensearch.logs.indexing_documents',
                         count=len(texts),
                         index=self.index_name)
        logger.info(log_msg)
        self.log(log_msg)

        return_ids = self._bulk_ingest_embeddings(
            client=client,
            index_name=self.index_name,
            embeddings=vectors,
            texts=texts,
            metadatas=metadatas,
            vector_field=self.vector_field,
            text_field="text",
            mapping=mapping,
            is_aoss=is_aoss,
        )
        self.log(metadatas)

        success_msg = i18n.t('components.elastic.opensearch.logs.successfully_indexed',
                             count=len(return_ids))
        logger.info(success_msg)
        self.log(success_msg)

    def _is_placeholder_term(self, term_obj: dict) -> bool:
        return any(v == "__IMPOSSIBLE_VALUE__" for v in term_obj.values())

    def _coerce_filter_clauses(self, filter_obj: dict | None) -> list[dict]:
        """Convert filter expressions into OpenSearch-compatible filter clauses."""
        if not filter_obj:
            return []

        if isinstance(filter_obj, str):
            try:
                filter_obj = json.loads(filter_obj)
                logger.debug(
                    i18n.t('components.elastic.opensearch.logs.filter_parsed'))
            except json.JSONDecodeError:
                logger.warning(
                    i18n.t('components.elastic.opensearch.logs.invalid_filter_json'))
                return []

        # Case A: explicit filters
        if "filter" in filter_obj:
            raw = filter_obj["filter"]
            if isinstance(raw, dict):
                raw = [raw]
            explicit_clauses: list[dict] = []
            for f in raw or []:
                if "term" in f and isinstance(f["term"], dict) and not self._is_placeholder_term(f["term"]):
                    explicit_clauses.append(f)
                elif "terms" in f and isinstance(f["terms"], dict):
                    field, vals = next(iter(f["terms"].items()))
                    if isinstance(vals, list) and len(vals) > 0:
                        explicit_clauses.append(f)
            logger.debug(i18n.t('components.elastic.opensearch.logs.explicit_filters',
                                count=len(explicit_clauses)))
            return explicit_clauses

        # Case B: context-style mapping
        field_mapping = {
            "data_sources": "filename",
            "document_types": "mimetype",
            "owners": "owner",
        }
        context_clauses: list[dict] = []
        for k, values in filter_obj.items():
            if not isinstance(values, list):
                continue
            field = field_mapping.get(k, k)
            if len(values) == 0:
                context_clauses.append(
                    {"term": {field: "__IMPOSSIBLE_VALUE__"}})
            elif len(values) == 1:
                if values[0] != "__IMPOSSIBLE_VALUE__":
                    context_clauses.append({"term": {field: values[0]}})
            else:
                context_clauses.append({"terms": {field: values}})
        logger.debug(i18n.t('components.elastic.opensearch.logs.context_filters',
                            count=len(context_clauses)))
        return context_clauses

    def search(self, query: str | None = None) -> list[dict[str, Any]]:
        """Perform hybrid search combining vector similarity and keyword matching."""
        logger.info(
            i18n.t('components.elastic.opensearch.logs.starting_hybrid_search'))
        logger.info(self.ingest_data)

        client = self.build_client()
        q = (query or "").strip()

        logger.debug(i18n.t('components.elastic.opensearch.logs.search_query',
                            query=q[:100] + ("..." if len(q) > 100 else "")))

        filter_obj = None
        if getattr(self, "filter_expression", "") and self.filter_expression.strip():
            try:
                filter_obj = json.loads(self.filter_expression)
                logger.debug(
                    i18n.t('components.elastic.opensearch.logs.filter_expression_parsed'))
            except json.JSONDecodeError as e:
                error_msg = i18n.t('components.elastic.opensearch.errors.invalid_filter_json',
                                   error=str(e))
                logger.error(error_msg)
                raise ValueError(error_msg) from e

        if not self.embedding:
            error_msg = i18n.t(
                'components.elastic.opensearch.errors.embedding_required_for_search')
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.debug(
            i18n.t('components.elastic.opensearch.logs.embedding_query'))
        vec = self.embedding.embed_query(q)

        filter_clauses = self._coerce_filter_clauses(filter_obj)

        limit = (filter_obj or {}).get("limit", self.number_of_results)
        score_threshold = (filter_obj or {}).get("score_threshold", 0)

        logger.debug(i18n.t('components.elastic.opensearch.logs.search_params',
                            limit=limit,
                            threshold=score_threshold,
                            filters=len(filter_clauses)))

        body = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "knn": {
                                self.vector_field: {
                                    "vector": vec,
                                    "k": 10,
                                    "boost": 0.7,
                                }
                            }
                        },
                        {
                            "multi_match": {
                                "query": q,
                                "fields": ["text^2", "filename^1.5"],
                                "type": "best_fields",
                                "fuzziness": "AUTO",
                                "boost": 0.3,
                            }
                        },
                    ],
                    "minimum_should_match": 1,
                }
            },
            "aggs": {
                "data_sources": {"terms": {"field": "filename", "size": 20}},
                "document_types": {"terms": {"field": "mimetype", "size": 10}},
                "owners": {"terms": {"field": "owner", "size": 10}},
            },
            "_source": [
                "filename",
                "mimetype",
                "page",
                "text",
                "source_url",
                "owner",
                "allowed_users",
                "allowed_groups",
            ],
            "size": limit,
        }
        if filter_clauses:
            body["query"]["bool"]["filter"] = filter_clauses

        if isinstance(score_threshold, (int, float)) and score_threshold > 0:
            body["min_score"] = score_threshold

        logger.debug(
            i18n.t('components.elastic.opensearch.logs.executing_search'))
        resp = client.search(index=self.index_name, body=body)
        hits = resp.get("hits", {}).get("hits", [])

        logger.info(i18n.t('components.elastic.opensearch.logs.search_completed',
                           count=len(hits)))

        return [
            {
                "page_content": hit["_source"].get("text", ""),
                "metadata": {k: v for k, v in hit["_source"].items() if k != "text"},
                "score": hit.get("_score"),
            }
            for hit in hits
        ]

    def search_documents(self) -> list[Data]:
        """Search documents and return results as Data objects."""
        try:
            logger.info(
                i18n.t('components.elastic.opensearch.logs.searching_documents'))
            raw = self.search(self.search_query or "")
            results = [Data(text=hit["page_content"], **hit["metadata"])
                       for hit in raw]
            logger.info(i18n.t('components.elastic.opensearch.logs.documents_found',
                               count=len(results)))
            self.log(self.ingest_data)
            return results
        except Exception as e:
            error_msg = i18n.t('components.elastic.opensearch.errors.search_documents_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.log(error_msg)
            raise

    async def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None) -> dict:
        """Dynamically update component configuration based on field changes."""
        try:
            if field_name == "auth_mode":
                mode = (field_value or "basic").strip().lower()
                is_basic = mode == "basic"
                is_jwt = mode == "jwt"

                logger.debug(i18n.t('components.elastic.opensearch.logs.auth_mode_changed',
                                    mode=mode))

                build_config["username"]["show"] = is_basic
                build_config["password"]["show"] = is_basic

                build_config["jwt_token"]["show"] = is_jwt
                build_config["jwt_header"]["show"] = is_jwt
                build_config["bearer_prefix"]["show"] = is_jwt

                build_config["username"]["required"] = is_basic
                build_config["password"]["required"] = is_basic

                build_config["jwt_token"]["required"] = is_jwt
                build_config["jwt_header"]["required"] = is_jwt
                build_config["bearer_prefix"]["required"] = False

                if is_basic:
                    build_config["jwt_token"]["value"] = ""

                return build_config

        except (KeyError, ValueError) as e:
            error_msg = i18n.t('components.elastic.opensearch.errors.update_config_failed',
                               error=str(e))
            logger.error(error_msg)
            self.log(error_msg)

        return build_config
