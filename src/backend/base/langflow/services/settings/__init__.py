"""Settings module with lazy settings instance access."""


def __getattr__(name):
    """Lazy loading of settings to avoid circular imports."""
    if name == "settings":
        from langflow.services.deps import get_settings_service

        return get_settings_service().settings
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


__all__ = ["settings"]
