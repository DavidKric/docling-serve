import uuid
import logging
from typing import Dict, Any, Optional, Protocol, Type, ClassVar, Callable
from abc import ABC, abstractmethod

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from docling_serve.semantic_document_augmentation.service import SemanticDocumentAugmentationExportService
from docling_serve.datamodel.responses import ConvertDocumentResponse
from fastapi.responses import FileResponse

_log = logging.getLogger(__name__)

# Protocol for document objects
class DoclingDocument(Protocol):
    """Protocol defining what constitutes a DoclingDocument"""
    # This ensures type checking without requiring the actual class
    pass

# Abstract Storage Backend
class StorageBackend(ABC):
    """Abstract storage backend that can be implemented for different storage solutions"""
    
    @abstractmethod
    def store_document(self, document: DoclingDocument) -> str:
        """Store a document and return its ID"""
        pass
    
    @abstractmethod
    def get_document(self, document_id: str) -> Optional[DoclingDocument]:
        """Retrieve a document by ID"""
        pass

# In-Memory Storage Backend (for tests)
class InMemoryStorage(StorageBackend):
    """In-memory document storage for testing"""
    _document_store: Dict[str, DoclingDocument] = {}
    
    def store_document(self, document: DoclingDocument) -> str:
        """Store a document in memory and return its ID"""
        doc_id = str(uuid.uuid4())
        self._document_store[doc_id] = document
        return doc_id
    
    def get_document(self, document_id: str) -> Optional[DoclingDocument]:
        """Retrieve a document from memory by ID"""
        return self._document_store.get(document_id)

# Blob Storage Backend (placeholder for production)
class BlobStorage(StorageBackend):
    """Blob storage implementation (placeholder)"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        # In production, you'd initialize your blob storage client here
    
    def store_document(self, document: DoclingDocument) -> str:
        """Store a document in blob storage and return its ID"""
        # In production, implement actual blob storage logic
        doc_id = str(uuid.uuid4())
        _log.info(f"Would store document in blob storage with ID: {doc_id}")
        return doc_id
    
    def get_document(self, document_id: str) -> Optional[DoclingDocument]:
        """Retrieve a document from blob storage by ID"""
        # In production, implement actual blob storage retrieval
        _log.info(f"Would retrieve document from blob storage with ID: {document_id}")
        return None

# DB Storage Backend (placeholder for production)
class DatabaseStorage(StorageBackend):
    """Database storage implementation (placeholder)"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        # In production, you'd initialize your database client here
    
    def store_document(self, document: DoclingDocument) -> str:
        """Store a document in database and return its ID"""
        # In production, implement actual database storage logic
        doc_id = str(uuid.uuid4())
        _log.info(f"Would store document in database with ID: {doc_id}")
        return doc_id
    
    def get_document(self, document_id: str) -> Optional[DoclingDocument]:
        """Retrieve a document from database by ID"""
        # In production, implement actual database retrieval
        _log.info(f"Would retrieve document from database with ID: {document_id}")
        return None

# Document Storage Service (uses the active backend)
class DocumentStorageService:
    """Service for document storage that uses the configured backend"""
    
    # Default to in-memory storage for tests
    _storage_backend: ClassVar[StorageBackend] = InMemoryStorage()
    
    @classmethod
    def configure_backend(cls, backend: StorageBackend) -> None:
        """Configure which storage backend to use"""
        cls._storage_backend = backend
        _log.info(f"Configured storage backend: {backend.__class__.__name__}")
    
    @classmethod
    def register_document(cls, document: DoclingDocument) -> str:
        """Register a document with the active backend"""
        return cls._storage_backend.store_document(document)
    
    @classmethod
    def get_document(cls, document_id: str) -> Optional[DoclingDocument]:
        """Retrieve a document using the active backend"""
        return cls._storage_backend.get_document(document_id)

# Helper function to extract document from conversion results
def _extract_document_from_response(response: ConvertDocumentResponse) -> Optional[DoclingDocument]:
    """Extract the DoclingDocument object from a conversion response"""
    # Try to get document from the conversion results
    if hasattr(response, '_conv_results') and response._conv_results:
        try:
            return response._conv_results[0].document
        except (AttributeError, IndexError):
            _log.warning("Could not extract document from _conv_results")
    
    # Try to get the JSON content if available
    if hasattr(response, 'document') and response.document:
        if hasattr(response.document, 'json_content') and response.document.json_content:
            return response.document.json_content
    
    _log.warning("Could not extract document from conversion response")
    return None

# FastAPI Middleware for Document Registration
class DocumentRegistrationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that intercepts responses from document conversion endpoints,
    extracts DoclingDocuments, and registers them with the DocumentStorageService.
    
    This middleware enables transparent document storage for routes from both
    the original app.py and the semantic_document_augmentation module.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Process the request and get the response
        response = await call_next(request)
        
        # Only process responses from document conversion endpoints
        if self._is_conversion_endpoint(request.url.path):
            # Handle FileResponse differently as it's a special case
            if isinstance(response, FileResponse):
                # File responses need special handling - maybe store by filename
                # or use a request attribute passed from the route handler
                # This is a placeholder for more complex logic if needed
                _log.debug(f"Skipping middleware document registration for FileResponse: {response.filename}")
                return response
            
            # For JSON responses (ConvertDocumentResponse), we can extract and store the document
            if isinstance(response, Response) and response.headers.get("content-type") == "application/json":
                try:
                    # Get the response body
                    body = b""
                    async for chunk in response.body_iterator:
                        body += chunk
                    
                    # Re-create iterator for response
                    response.body_iterator = iter([body])
                    
                    # Parse as ConvertDocumentResponse
                    import json
                    from pydantic import parse_raw_as
                    
                    data = json.loads(body.decode())
                    
                    # Check if data contains a 'document' field (sign it's a ConvertDocumentResponse)
                    if isinstance(data, dict) and "document" in data:
                        # Create a temporary ConvertDocumentResponse to pass to extract function
                        temp_response = type("TempResponse", (), {"document": data["document"]})()
                        
                        # Extract and register the document
                        doc = _extract_document_from_response(temp_response)
                        if doc:
                            doc_id = DocumentStorageService.register_document(doc)
                            _log.info(f"Middleware registered document with ID: {doc_id}")
                            
                            # Modify the response to include the document ID
                            if "document" in data and isinstance(data["document"], dict):
                                data["document"]["id"] = doc_id
                                modified_body = json.dumps(data).encode()
                                
                                # Update headers with new content length
                                response.headers["content-length"] = str(len(modified_body))
                                
                                # Return a new response with the modified body
                                from starlette.responses import JSONResponse
                                return JSONResponse(
                                    content=data,
                                    status_code=response.status_code,
                                    headers=dict(response.headers),
                                )
                except Exception as e:
                    _log.error(f"Error in document registration middleware: {str(e)}")
                    # Return the original response in case of errors
                    pass
        
        return response
    
    def _is_conversion_endpoint(self, path: str) -> bool:
        """Check if the path is a document conversion endpoint"""
        conversion_paths = [
            # Original app.py routes
            "/v1alpha/convert/source",
            "/v1alpha/convert/file",
            "/v1alpha/result/",  # For async conversion results
            
            # Semantic document augmentation routes 
            "/semantic-document-augmentation/convert/source",
            "/semantic-document-augmentation/convert/file",
            "/semantic-document-augmentation/result/"
        ]
        
        return any(path.startswith(p) for p in conversion_paths)