"""
Flaskz execution context management.

Provides a framework-independent execution context based on ContextVar,
supporting Flask, FastAPI, Celery, and standalone Python applications.

.. versionadded:: 1.9.1

Public APIs include:
    - Framework integration: Flask and FastAPI request context initialization.
    - Context lifecycle: Create, access, and end execution contexts.
    - Context scope: Manage context lifecycle using a context manager.
    - Context data: Store, retrieve, and remove context-specific values.
    - Resource cleanup: Register cleanup callbacks for context termination.
"""

__all__ = [
    'begin_context', 'end_context', 'register_context_cleanup',
    'has_context', 'get_context_key',
    'has_context_value', 'set_context_value', 'get_context_value', 'remove_context_value',
    'set_context_values', 'get_context_values', 'clear_context_values',
    'set_context_option', 'get_context_option',
    'context_scope',

    'init_flask_request_context', 'init_fastapi_request_context',
    'get_request_context_value', 'set_request_context_value',
    'set_context_db_session_cache_enabled', 'get_context_db_session_cache_enabled'
]

from .app_context import get_context_db_session_cache_enabled, get_request_context_value, init_fastapi_request_context, init_flask_request_context, set_context_db_session_cache_enabled, \
    set_request_context_value
from .context import begin_context, clear_context_values, context_scope, end_context, get_context_key, get_context_option, get_context_value, get_context_values, \
    has_context, has_context_value, register_context_cleanup, remove_context_value, set_context_option, set_context_value, set_context_values
