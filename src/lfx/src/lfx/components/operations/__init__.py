"""ETL Operation Components."""

from importlib import import_module

_dynamic_imports = {
    "ETLDualStreamJoinComponent": "dual_stream_join",
    "ETLMultiStreamUnionComponent": "multi_stream_union",
    "ETLGroupByComponent": "group_by",
    "ETLDeduplicationComponent": "deduplication",
}


def __getattr__(attr_name: str):
    """Lazy import for ETL operation components."""
    if attr_name not in _dynamic_imports:
        msg = f"module {__name__!r} has no attribute {attr_name!r}"
        raise AttributeError(msg)

    module_name = _dynamic_imports[attr_name]
    module = import_module(f".{module_name}", package=__name__)
    component_class = getattr(module, attr_name)
    globals()[attr_name] = component_class
    return component_class


__all__ = list(_dynamic_imports.keys())
