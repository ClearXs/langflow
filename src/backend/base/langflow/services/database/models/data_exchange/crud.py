from uuid import UUID

from lfx.log.logger import logger
from sqlmodel import col, delete, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from langflow.services.database.models.data_exchange.model import (
    DataExchangeBase,
    DataExchangeReadResponse,
    DataExchangeStatsResponse,
    DataExchangeTable,
    VertexExchangeResponse,
)
from langflow.services.deps import get_settings_service


async def log_data_exchange(db: AsyncSession, exchange: DataExchangeBase) -> DataExchangeTable | None:
    """Log a data exchange record and maintain a maximum number of exchanges in the database.

    This function logs a new data exchange into the database and ensures that the number of exchanges
    does not exceed the maximum limit (following the transaction limit). If the number of exchanges
    exceeds the limit, the oldest exchanges are deleted to maintain the limit.

    Args:
        db: Database session
        exchange: Data exchange data to log

    Returns:
        The created DataExchangeTable entry

    Raises:
        IntegrityError: If there is a database integrity error
    """
    if not exchange.transaction_id:
        await logger.adebug("DataExchange transaction_id is None")
        return None

    table = DataExchangeTable(**exchange.model_dump())

    try:
        # Get max entries setting (use same limit as transactions)
        max_entries = get_settings_service().settings.max_transactions_to_keep

        # Delete older entries for this transaction in a single transaction
        delete_older = delete(DataExchangeTable).where(
            DataExchangeTable.transaction_id == exchange.transaction_id,
            col(DataExchangeTable.id).in_(
                select(DataExchangeTable.id)
                .where(DataExchangeTable.transaction_id == exchange.transaction_id)
                .order_by(col(DataExchangeTable.timestamp).desc())
                .offset(max_entries - 1)
            ),
        )

        # Add new entry and execute delete in same transaction
        db.add(table)
        await db.exec(delete_older)
        await db.commit()

    except Exception:
        await db.rollback()
        raise
    return table


async def log_data_exchanges_bulk(db: AsyncSession, exchanges: list[DataExchangeBase]) -> list[DataExchangeTable]:
    """Bulk log multiple data exchange records.

    Args:
        db: Database session
        exchanges: List of data exchange data to log

    Returns:
        List of created DataExchangeTable entries
    """
    if not exchanges:
        return []

    tables = [DataExchangeTable(**exchange.model_dump()) for exchange in exchanges]

    try:
        db.add_all(tables)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return tables


async def get_data_exchanges_by_transaction_id(
    db: AsyncSession, transaction_id: UUID, limit: int | None = 1000
) -> list[DataExchangeTable]:
    """Get all data exchanges for a specific transaction.

    Args:
        db: Database session
        transaction_id: Transaction UUID
        limit: Maximum number of records to return

    Returns:
        List of DataExchangeTable entries
    """
    stmt = (
        select(DataExchangeTable)
        .where(DataExchangeTable.transaction_id == transaction_id)
        .order_by(col(DataExchangeTable.timestamp))
        .limit(limit)
    )

    exchanges = await db.exec(stmt)
    return list(exchanges)


async def get_data_exchanges_by_flow_id(
    db: AsyncSession,
    flow_id: UUID,
    source_vertex_id: str | None = None,
    target_vertex_id: str | None = None,
    exchange_type: str | None = None,
    limit: int | None = 1000,
) -> list[DataExchangeTable]:
    """Get data exchanges for a flow with optional filters.

    Args:
        db: Database session
        flow_id: Flow UUID
        source_vertex_id: Optional source vertex filter
        target_vertex_id: Optional target vertex filter
        exchange_type: Optional exchange type filter
        limit: Maximum number of records to return

    Returns:
        List of DataExchangeTable entries
    """
    # Join with TransactionTable to filter by flow_id
    from langflow.services.database.models.transactions.model import TransactionTable

    stmt = (
        select(DataExchangeTable)
        .join(TransactionTable, DataExchangeTable.transaction_id == TransactionTable.id)
        .where(TransactionTable.flow_id == flow_id)
    )

    if source_vertex_id:
        stmt = stmt.where(DataExchangeTable.source_vertex_id == source_vertex_id)
    if target_vertex_id:
        stmt = stmt.where(DataExchangeTable.target_vertex_id == target_vertex_id)
    if exchange_type:
        stmt = stmt.where(DataExchangeTable.exchange_type == exchange_type)

    stmt = stmt.order_by(col(DataExchangeTable.timestamp).desc()).limit(limit)

    exchanges = await db.exec(stmt)
    return list(exchanges)


async def get_vertex_exchanges(
    db: AsyncSession, flow_id: UUID, vertex_id: str, limit: int | None = 100
) -> VertexExchangeResponse:
    """Get all input and output exchanges for a specific vertex.

    Args:
        db: Database session
        flow_id: Flow UUID
        vertex_id: Vertex ID
        limit: Maximum number of records per direction

    Returns:
        VertexExchangeResponse with input and output exchanges
    """
    from langflow.services.database.models.transactions.model import TransactionTable

    # Get input exchanges (where vertex is target)
    input_stmt = (
        select(DataExchangeTable)
        .join(TransactionTable, DataExchangeTable.transaction_id == TransactionTable.id)
        .where(TransactionTable.flow_id == flow_id, DataExchangeTable.target_vertex_id == vertex_id)
        .order_by(col(DataExchangeTable.timestamp).desc())
        .limit(limit)
    )

    # Get output exchanges (where vertex is source)
    output_stmt = (
        select(DataExchangeTable)
        .join(TransactionTable, DataExchangeTable.transaction_id == TransactionTable.id)
        .where(TransactionTable.flow_id == flow_id, DataExchangeTable.source_vertex_id == vertex_id)
        .order_by(col(DataExchangeTable.timestamp).desc())
        .limit(limit)
    )

    input_exchanges_raw = await db.exec(input_stmt)
    output_exchanges_raw = await db.exec(output_stmt)

    input_exchanges = [DataExchangeReadResponse.model_validate(e, from_attributes=True) for e in input_exchanges_raw]
    output_exchanges = [DataExchangeReadResponse.model_validate(e, from_attributes=True) for e in output_exchanges_raw]

    # Calculate totals
    total_input_count = len(input_exchanges)
    total_output_count = len(output_exchanges)
    total_input_size = sum(e.data_size for e in input_exchanges)
    total_output_size = sum(e.data_size for e in output_exchanges)

    return VertexExchangeResponse(
        vertex_id=vertex_id,
        input_exchanges=input_exchanges,
        output_exchanges=output_exchanges,
        total_input_count=total_input_count,
        total_output_count=total_output_count,
        total_input_size=total_input_size,
        total_output_size=total_output_size,
    )


async def get_data_exchange_stats(db: AsyncSession, flow_id: UUID) -> DataExchangeStatsResponse:
    """Get aggregated statistics for data exchanges in a flow.

    Args:
        db: Database session
        flow_id: Flow UUID

    Returns:
        DataExchangeStatsResponse with aggregated statistics
    """
    from langflow.services.database.models.transactions.model import TransactionTable

    # Total count and size
    stmt = (
        select(
            func.count(DataExchangeTable.id).label("total_exchanges"),
            func.sum(DataExchangeTable.data_size).label("total_data_size"),
            func.count(func.distinct(DataExchangeTable.source_vertex_id)).label("unique_source_vertices"),
            func.count(func.distinct(DataExchangeTable.target_vertex_id)).label("unique_target_vertices"),
        )
        .join(TransactionTable, DataExchangeTable.transaction_id == TransactionTable.id)
        .where(TransactionTable.flow_id == flow_id)
    )

    result = await db.exec(stmt)
    stats = result.one()

    total_exchanges = stats.total_exchanges or 0
    total_data_size = stats.total_data_size or 0
    unique_source_vertices = stats.unique_source_vertices or 0
    unique_target_vertices = stats.unique_target_vertices or 0

    # Exchange by type
    type_stmt = (
        select(DataExchangeTable.exchange_type, func.count(DataExchangeTable.id).label("count"))
        .join(TransactionTable, DataExchangeTable.transaction_id == TransactionTable.id)
        .where(TransactionTable.flow_id == flow_id)
        .group_by(DataExchangeTable.exchange_type)
    )

    type_results = await db.exec(type_stmt)
    exchange_by_type = {row.exchange_type: row.count for row in type_results}

    avg_data_size = total_data_size / total_exchanges if total_exchanges > 0 else 0.0

    return DataExchangeStatsResponse(
        total_exchanges=total_exchanges,
        total_data_size=total_data_size,
        unique_source_vertices=unique_source_vertices,
        unique_target_vertices=unique_target_vertices,
        exchange_by_type=exchange_by_type,
        avg_data_size=avg_data_size,
    )


async def delete_data_exchanges_by_transaction_id(db: AsyncSession, transaction_id: UUID) -> None:
    """Delete all data exchanges for a specific transaction.

    Args:
        db: Database session
        transaction_id: Transaction UUID
    """
    stmt = delete(DataExchangeTable).where(DataExchangeTable.transaction_id == transaction_id)
    await db.exec(stmt)
    await db.commit()


def transform_data_exchange_table(
    exchange: list[DataExchangeTable] | DataExchangeTable,
) -> list[DataExchangeReadResponse] | DataExchangeReadResponse:
    """Transform DataExchangeTable to DataExchangeReadResponse.

    Args:
        exchange: Single exchange or list of exchanges

    Returns:
        Transformed response(s)
    """
    if isinstance(exchange, list):
        return [DataExchangeReadResponse.model_validate(e, from_attributes=True) for e in exchange]
    return DataExchangeReadResponse.model_validate(exchange, from_attributes=True)
