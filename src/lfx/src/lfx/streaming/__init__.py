"""LFX Streaming Infrastructure.

This module provides the core infrastructure for real-time streaming execution
of components in LFX graphs.
"""

from lfx.streaming.protocol import StreamingComponent, is_streaming_component, streaming_component

__all__ = [
    "StreamingComponent",
    "is_streaming_component",
    "streaming_component",
]
