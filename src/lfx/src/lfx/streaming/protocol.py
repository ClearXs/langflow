"""Streaming protocol and interfaces for LFX components.

This module defines the core protocols and markers for streaming components.
"""

from collections.abc import AsyncGenerator, Generator
from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


@runtime_checkable
class StreamingComponent(Protocol):
    """Protocol for components that support streaming output.

    A streaming component yields data items one at a time using a Generator
    or AsyncGenerator, enabling real-time data flow through the graph.
    """

    is_streaming_component: bool

    def _should_stop_streaming(self) -> bool:
        """Check if streaming should stop.

        Returns:
            True if streaming should stop, False otherwise
        """
        ...


def streaming_component(cls):
    """Decorator to mark a component as supporting streaming.

    Usage:
        @streaming_component
        class MyStreamingComponent(Component):
            def stream_data(self) -> Generator[Data, None, None]:
                while not self._should_stop:
                    yield Data(...)
    """
    cls.is_streaming_component = True
    return cls


def is_streaming_component(component) -> bool:
    """Check if a component is a streaming component.

    Args:
        component: Component instance or class to check

    Returns:
        True if the component supports streaming, False otherwise
    """
    return getattr(component, "is_streaming_component", False)


def is_streaming_output(output) -> bool:
    """Check if an output is a streaming type.

    Args:
        output: Output value to check

    Returns:
        True if output is Generator or AsyncGenerator, False otherwise
    """
    return isinstance(output, (Generator, AsyncGenerator))
