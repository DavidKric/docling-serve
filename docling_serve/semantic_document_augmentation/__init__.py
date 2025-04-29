"""
Semantic Document Augmentation API Module

This module provides routes for document parsing and semantic entity extraction 
compatible with Papermage-style entities (paragraphs, sentences, tokens, etc).

The architecture uses a middleware-based approach for document storage:

1. DocumentRegistrationMiddleware:
   - Intercepts responses from conversion endpoints 
   - Extracts DoclingDocument objects from the responses
   - Registers them with DocumentStorageService
   - Adds document IDs to the JSON responses
   - Works with both original app routes and semantic document routes

2. DocumentStorageService:
   - Manages storage of DoclingDocument objects using configurable backends
   - Provides document retrieval by ID for all entity extraction endpoints
   - Supports in-memory storage (default) and placeholder implementations for
     blob storage and database storage

3. Routes:
   - Provide document conversion endpoints that mirror the app.py routes
   - Offer entity extraction endpoints (paragraphs, sentences, etc.)
   - Use DocumentStorageService to retrieve documents by ID
   
The middleware approach allows seamless document storage without modifying
the original conversion handlers or requiring routes to wrap each other.
"""

from .routes import router
from .middleware import DocumentRegistrationMiddleware, DocumentStorageService

__all__ = ["router", "DocumentRegistrationMiddleware", "DocumentStorageService"]