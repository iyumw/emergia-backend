"""
Custom exceptions for the emergy calculation engine.

These exceptions provide more specific error types than generic ValueError,
making it easier to write robust tests and error handling.
"""


class EmergyError(Exception):
    """Base exception for all emergy-related errors."""
    pass


class InvalidGraphError(EmergyError):
    """Raised when the graph structure is invalid (e.g., empty, cycles without break)."""
    pass


class NodeNotFoundError(EmergyError):
    """Raised when a referenced node does not exist in the graph."""
    pass


class InvalidNodeError(EmergyError):
    """Raised when a node has invalid properties (e.g., missing UEV for sources)."""
    pass


class InvalidEdgeError(EmergyError):
    """Raised when an edge references non-existent nodes or has invalid properties."""
    pass
