"""API endpoints for lineage analysis."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, status
from lfx.log import logger
from pydantic import BaseModel

from langflow.api.utils import CurrentActiveUser, DbSession
from langflow.services.database.models.flow.model import Flow
from langflow.services.lineage.service import LineageAnalyzer

router = APIRouter(prefix="/flows", tags=["Lineage"])


class LineageSearchRequest(BaseModel):
    """Request model for lineage search."""

    table_name: str


@router.get("/{flow_id}/lineage")
async def get_flow_lineage(
    flow_id: UUID,
    table_name: str | None = None,
    session: DbSession = None,
    current_user: CurrentActiveUser = None,
) -> dict[str, Any]:
    """Get data lineage for a flow.

    Args:
        flow_id: Flow UUID
        table_name: Optional table name to filter results (fuzzy match)
        session: Database session
        current_user: Current authenticated user

    Returns:
        Dictionary containing:
        - flow_id: Flow UUID
        - flow_name: Flow name
        - tables: List of table nodes with metadata
        - relationships: List of lineage relationships
        - total_tables: Total number of tables found
        - total_relationships: Total number of relationships

    Raises:
        HTTPException: If flow not found or user unauthorized
    """
    try:
        # Get flow from database
        flow = await session.get(Flow, flow_id)

        if not flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Flow {flow_id} not found",
            )

        # Check user authorization
        if flow.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this flow",
            )

        # Check if flow has data
        if not flow.data:
            return {
                "flow_id": str(flow_id),
                "flow_name": flow.name,
                "tables": [],
                "relationships": [],
                "total_tables": 0,
                "total_relationships": 0,
            }

        # Analyze lineage
        analyzer = LineageAnalyzer(flow.data)
        lineage_result = analyzer.analyze(table_name=table_name)

        # Add flow metadata
        return {
            "flow_id": str(flow_id),
            "flow_name": flow.name,
            "flow_description": flow.description,
            **lineage_result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error analyzing lineage for flow {flow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze lineage: {e!s}",
        ) from e


@router.get("/{flow_id}/lineage/tables")
async def get_flow_tables(
    flow_id: UUID,
    session: DbSession = None,
    current_user: CurrentActiveUser = None,
) -> dict[str, Any]:
    """Get all table nodes in a flow.

    Args:
        flow_id: Flow UUID
        session: Database session
        current_user: Current authenticated user

    Returns:
        Dictionary containing:
        - tables: List of all table nodes
        - source_tables: List of source/input tables
        - target_tables: List of target/output tables

    Raises:
        HTTPException: If flow not found or user unauthorized
    """
    try:
        # Get flow from database
        flow = await session.get(Flow, flow_id)

        if not flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Flow {flow_id} not found",
            )

        # Check user authorization
        if flow.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this flow",
            )

        # Check if flow has data
        if not flow.data:
            return {
                "tables": [],
                "source_tables": [],
                "target_tables": [],
            }

        # Extract tables
        analyzer = LineageAnalyzer(flow.data)
        tables = analyzer.extract_table_nodes()

        source_tables = [t for t in tables if t["type"] == "source"]
        target_tables = [t for t in tables if t["type"] == "target"]

        return {
            "tables": tables,
            "source_tables": source_tables,
            "target_tables": target_tables,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error extracting tables from flow {flow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract tables: {e!s}",
        ) from e


# Global lineage search endpoints (without flow_id)
lineage_router = APIRouter(prefix="/lineage", tags=["Lineage"])


@lineage_router.post("/search")
async def search_lineage_by_table(
    request: LineageSearchRequest = Body(...),
    session: DbSession = None,
    current_user: CurrentActiveUser = None,
) -> dict[str, Any]:
    """Search data lineage across all user flows by table name.

    Searches for the specified table name (exact match) across all flows
    owned by the current user. Uses async optimization for performance.

    Args:
        request: Request body containing table_name
        session: Database session
        current_user: Current authenticated user

    Returns:
        Dictionary containing:
        - results: List of flows with matching tables and their lineage
          [
            {
              "flow": {"flow_id", "flow_name", "flow_description"},
              "lineage": {"tables", "relationships", "total_tables", "total_relationships"}
            }
          ]
        - total_flows_searched: Total number of flows analyzed
        - total_flows_matched: Number of flows with matching tables

    Raises:
        HTTPException: If search fails
    """
    try:
        from sqlmodel import select

        # 1. Query all user flows
        stmt = select(Flow).where(Flow.user_id == current_user.id)
        result = await session.exec(stmt)
        flows: list[Flow] = result.all()

        logger.info(f"Searching for table '{request.table_name}' across {len(flows)} flows")

        if not flows:
            return {
                "results": [],
                "total_flows_searched": 0,
                "total_flows_matched": 0,
            }

        # 2. Analyze flows concurrently in batches
        batch_size = 10
        all_results = []

        for i in range(0, len(flows), batch_size):
            batch = flows[i : i + batch_size]

            # Analyze batch concurrently
            tasks = [_analyze_single_flow(flow, request.table_name) for flow in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Collect valid results
            for flow, lineage_result in zip(batch, batch_results, strict=False):
                if isinstance(lineage_result, Exception):
                    logger.warning(f"Error analyzing flow {flow.id}: {lineage_result}")
                    continue

                if isinstance(lineage_result, dict) and lineage_result.get("tables"):
                    all_results.append(
                        {
                            "flow": {
                                "flow_id": str(flow.id),
                                "flow_name": flow.name,
                                "flow_description": flow.description,
                            },
                            "lineage": lineage_result,
                        }
                    )

        logger.info(
            f"Search completed: {len(flows)} flows searched, {len(all_results)} matches found"
        )

        return {
            "results": all_results,
            "total_flows_searched": len(flows),
            "total_flows_matched": len(all_results),
        }

    except Exception as e:
        logger.exception(f"Error searching lineage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search lineage: {e!s}",
        ) from e


async def _analyze_single_flow(flow: Flow, table_name: str) -> dict[str, Any]:
    """Analyze a single flow for the target table.

    Args:
        flow: Flow object to analyze
        table_name: Table name to search for (exact match)

    Returns:
        Lineage analysis result or empty dict
    """
    try:
        if not flow.data:
            return {}

        import asyncio

        # Analyze with exact match and 30 second timeout
        analyzer = LineageAnalyzer(flow.data)
        result = await asyncio.wait_for(
            asyncio.to_thread(
                analyzer.analyze,
                table_name=table_name,
                exact_match=True,
            ),
            timeout=30.0,
        )
        return result

    except asyncio.TimeoutError:
        logger.warning(f"Timeout analyzing flow {flow.id}")
        return {}
    except Exception as e:
        logger.warning(f"Error analyzing flow {flow.id}: {e}")
        return {}


# Export both routers
__all__ = ["lineage_router", "router"]
