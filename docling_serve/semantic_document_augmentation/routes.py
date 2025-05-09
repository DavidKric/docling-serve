# papermage_routes.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File, Form, Request
from typing import Annotated, Dict, Any, List, Optional, Union, Callable, TypeVar
import asyncio
import logging
import uuid
from io import BytesIO

from .schemas import ParagraphsResponse, SentencesResponse, TokensResponse, SectionsResponse, TitlesResponse, AuthorsResponse, TablesResponse, FiguresResponse, CaptionsResponse, FootnotesResponse, HeadersResponse, FootersResponse, ListsResponse, AlgorithmsResponse, EquationsResponse, ReferencesResponse, PapermageDocumentResponse
from .service import SemanticDocumentAugmentationExportService
from docling_serve.engines import get_orchestrator
from docling_serve.engines.async_local.orchestrator import AsyncLocalOrchestrator
from docling_serve.datamodel.responses import TaskStatusResponse, MessageKind, WebsocketMessage, ConvertDocumentResponse
from docling_serve.datamodel.convert import ConvertDocumentsOptions
from docling_serve.datamodel.requests import ConvertDocumentsRequest, HttpSource, ConvertDocumentFileSourcesRequest
from docling.datamodel.base_models import DocumentStream
from docling_serve.docling_conversion import convert_documents
from docling_serve.response_preparation import process_results
from docling_serve.helper_functions import FormDepends
from .middleware import DocumentStorageService

_log = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Semantic Document Augmentation"])

# Helper function to fetch document with proper error handling
async def _fetch_docling_document(document_id: str):
    """Get a document from the storage service by ID"""
    doc = DocumentStorageService.get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

# Convert a document from URL(s)
@router.post(
    "/convert/source",
    response_model=ConvertDocumentResponse,
    responses={
        200: {
            "content": {"application/zip": {}},
        }
    },
)
def process_url(
    background_tasks: BackgroundTasks, conversion_request: ConvertDocumentsRequest
):
    """
    Convert documents from URLs or sources.
    
    The document registration will be handled automatically by middleware.
    """
    # Parse sources
    sources: list[Union[str, DocumentStream]] = []
    headers: Optional[dict[str, Any]] = None
    if isinstance(conversion_request, ConvertDocumentFileSourcesRequest):
        for file_source in conversion_request.file_sources:
            sources.append(file_source.to_document_stream())
    else:
        for http_source in conversion_request.http_sources:
            sources.append(http_source.url)
            if headers is None and http_source.headers:
                headers = http_source.headers

    # Convert documents
    results = convert_documents(
        sources=sources, options=conversion_request.options, headers=headers
    )

    # Process results
    response = process_results(
        background_tasks=background_tasks,
        conversion_options=conversion_request.options,
        conv_results=results,
    )
    
    return response

# Convert a document from file(s)
@router.post(
    "/convert/file",
    response_model=ConvertDocumentResponse,
    responses={
        200: {
            "content": {"application/zip": {}},
        }
    },
)
async def process_file(
    background_tasks: BackgroundTasks,
    files: list[UploadFile],
    options: Annotated[
        ConvertDocumentsOptions, FormDepends(ConvertDocumentsOptions)
    ],
):
    """
    Convert uploaded documents.
    
    The document registration will be handled automatically by middleware.
    """
    _log.info(f"Received {len(files)} files for processing.")

    # Load files
    file_sources = []
    for file in files:
        buf = BytesIO(await file.read())
        name = file.filename if file.filename else "file.pdf"
        file_sources.append(DocumentStream(name=name, stream=buf))

    # Convert documents
    results = convert_documents(sources=file_sources, options=options)

    # Process results
    response = process_results(
        background_tasks=background_tasks,
        conversion_options=options,
        conv_results=results,
    )
    
    return response

# Convert a document from URL(s) using the async api
@router.post(
    "/convert/source/async",
    response_model=TaskStatusResponse,
)
async def process_url_async(
    orchestrator: Annotated[AsyncLocalOrchestrator, Depends(get_orchestrator)],
    conversion_request: ConvertDocumentsRequest,
):
    """
    Asynchronously convert documents from URLs with task tracking.
    
    Document registration will be handled by middleware when results are retrieved.
    """
    task = await orchestrator.enqueue(request=conversion_request)
    task_queue_position = await orchestrator.get_queue_position(
        task_id=task.task_id
    )
    
    return TaskStatusResponse(
        task_id=task.task_id,
        task_status=task.task_status,
        task_position=task_queue_position,
    )

# Get result of async task
@router.get(
    "/result/{task_id}",
    response_model=ConvertDocumentResponse,
    responses={
        200: {
            "content": {"application/zip": {}},
        }
    },
)
async def task_result(
    orchestrator: Annotated[AsyncLocalOrchestrator, Depends(get_orchestrator)],
    task_id: str,
):
    """
    Retrieve the result of an asynchronous conversion task.
    
    Document registration will be handled automatically by middleware.
    """
    try:
        result = await orchestrator.get_result(task_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving task result: {str(e)}")

@router.get("/paragraphs", response_model=ParagraphsResponse)
async def get_paragraphs(document_id: str):
    """
    Retrieve all paragraphs from the document as Papermage-style entities.
    
    Each paragraph is returned with its full text and bounding box coordinates on the page, 
    analogous to Papermage's text block segmentation (paragraphs).
    """
    doc = await _fetch_docling_document(document_id)
    para_entities = SemanticDocumentAugmentationExportService.extract_paragraphs(doc)
    return {"entities": para_entities}

@router.get("/paragraphs/async", response_model=TaskStatusResponse)
async def get_paragraphs_async(
    orchestrator: Annotated[AsyncLocalOrchestrator, Depends(get_orchestrator)],
    document_id: str
):
    """
    Asynchronously retrieve all paragraphs from the document.
    
    Returns a task ID that can be used to poll for results.
    """
    task = await orchestrator.enqueue(
        request={"operation": "extract_paragraphs", "document_id": document_id}
    )
    task_queue_position = await orchestrator.get_queue_position(task_id=task.task_id)
    return TaskStatusResponse(
        task_id=task.task_id,
        task_status=task.task_status,
        task_position=task_queue_position,
    )

@router.get("/sentences", response_model=SentencesResponse)
async def get_sentences(document_id: str):
    """
    Retrieve all sentences from the document in Papermage-style format.
    
    Splits paragraphs into sentences using punctuation heuristics. Each sentence 
    is returned with its text and an approximate bounding box.
    """
    doc = await _fetch_docling_document(document_id)
    sentence_entities = SemanticDocumentAugmentationExportService.extract_sentences(doc)
    return {"entities": sentence_entities}

@router.get("/tokens", response_model=TokensResponse)
async def get_tokens(document_id: str):
    """
    Retrieve all tokens (words and symbols) from the document in Papermage-style format.
    
    Each token is provided with the token text and an approximate bounding box. This is analogous 
    to Papermage's token layer, though precise coordinates may be approximated.
    """
    doc = await _fetch_docling_document(document_id)
    token_entities = SemanticDocumentAugmentationExportService.extract_tokens(doc)
    return {"entities": token_entities}

@router.get("/sections", response_model=SectionsResponse)
async def get_sections(document_id: str):
    """
    Retrieve the section headings of the document.
    
    Each section (e.g., a major heading in the document) is returned with its heading text and location,
    analogous to Papermage's section entities.
    """
    doc = await _fetch_docling_document(document_id)
    section_entities = SemanticDocumentAugmentationExportService.extract_sections(doc)
    return {"entities": section_entities}

@router.get("/titles", response_model=TitlesResponse)
async def get_titles(document_id: str):
    """
    Retrieve the document title in Papermage-style format.
    
    Returns the title text of the document with its bounding box. In most cases, this is the main heading on the first page.
    """
    doc = await _fetch_docling_document(document_id)
    title_entities = SemanticDocumentAugmentationExportService.extract_title(doc)
    return {"entities": title_entities}

@router.get("/authors", response_model=AuthorsResponse)
async def get_authors(document_id: str):
    """
    Retrieve the document authors in Papermage-style format.
    
    Attempts to identify author lines (usually immediately below the title on the first page). 
    Each author entry (or the whole author line) is returned with text and bounding box.
    """
    doc = await _fetch_docling_document(document_id)
    author_entities = SemanticDocumentAugmentationExportService.extract_authors(doc)
    return {"entities": author_entities}

# Tables are computationally expensive, so use background tasks and add async version
@router.get("/tables", response_model=TablesResponse)
async def get_tables(
    background_tasks: BackgroundTasks,
    document_id: str
):
    """
    Retrieve all tables in the document in Papermage-style format.
    
    Each table is returned with a flattened text representation of its contents and its bounding box on the page.
    """
    doc = await _fetch_docling_document(document_id)
    
    # Initialize empty result
    table_entities = []
    
    # Add the extraction to background tasks
    background_tasks.add_task(
        _extract_tables_background,
        doc, 
        table_entities
    )
    
    return {"entities": table_entities}

@router.get("/tables/async", response_model=TaskStatusResponse)
async def get_tables_async(
    orchestrator: Annotated[AsyncLocalOrchestrator, Depends(get_orchestrator)],
    document_id: str
):
    """
    Asynchronously retrieve all tables from the document.
    
    Table extraction can be computationally expensive. This endpoint returns a task ID
    that can be used to poll for results.
    """
    # Verify document exists first
    await _fetch_docling_document(document_id)
    
    task = await orchestrator.enqueue(
        request={"operation": "extract_tables", "document_id": document_id}
    )
    task_queue_position = await orchestrator.get_queue_position(task_id=task.task_id)
    return TaskStatusResponse(
        task_id=task.task_id,
        task_status=task.task_status,
        task_position=task_queue_position,
    )

# Background task helper for table extraction
async def _extract_tables_background(doc, result_list):
    """Background task to extract tables without blocking the response"""
    try:
        entities = SemanticDocumentAugmentationExportService.extract_tables(doc)
        result_list.extend(entities)
        _log.info(f"Extracted {len(entities)} tables successfully")
    except Exception as e:
        _log.error(f"Error extracting tables: {str(e)}")

# Figures are also computationally expensive
@router.get("/figures", response_model=FiguresResponse)
async def get_figures(
    background_tasks: BackgroundTasks,
    document_id: str
):
    """
    Retrieve all figures (images) from the document in Papermage-style format.
    
    Each figure is represented by its bounding box. (No textual content is included for figures.)
    """
    doc = await _fetch_docling_document(document_id)
    
    # Initialize empty result
    figure_entities = []
    
    # Add the extraction to background tasks
    background_tasks.add_task(
        _extract_figures_background,
        doc, 
        figure_entities
    )
    
    return {"entities": figure_entities}

@router.get("/figures/async", response_model=TaskStatusResponse)
async def get_figures_async(
    orchestrator: Annotated[AsyncLocalOrchestrator, Depends(get_orchestrator)],
    document_id: str
):
    """
    Asynchronously retrieve all figures from the document.
    
    Figure extraction can be computationally expensive. This endpoint returns a task ID
    that can be used to poll for results.
    """
    # Verify document exists first
    await _fetch_docling_document(document_id)
    
    task = await orchestrator.enqueue(
        request={"operation": "extract_figures", "document_id": document_id}
    )
    task_queue_position = await orchestrator.get_queue_position(task_id=task.task_id)
    return TaskStatusResponse(
        task_id=task.task_id,
        task_status=task.task_status,
        task_position=task_queue_position,
    )

# Background task helper for figure extraction
async def _extract_figures_background(doc, result_list):
    """Background task to extract figures without blocking the response"""
    try:
        entities = SemanticDocumentAugmentationExportService.extract_figures(doc)
        result_list.extend(entities)
        _log.info(f"Extracted {len(entities)} figures successfully")
    except Exception as e:
        _log.error(f"Error extracting figures: {str(e)}")

@router.get("/captions", response_model=CaptionsResponse)
async def get_captions(document_id: str):
    """
    Retrieve all figure and table captions in the document.
    
    Each caption (figure or table description text) is returned with its text content and bounding box.
    """
    doc = await _fetch_docling_document(document_id)
    caption_entities = SemanticDocumentAugmentationExportService.extract_captions(doc)
    return {"entities": caption_entities}

@router.get("/footnotes", response_model=FootnotesResponse)
async def get_footnotes(document_id: str):
    """
    Retrieve all footnotes from the document.
    
    Each footnote is returned with its text content and bounding box (typically at the bottom of a page).
    """
    doc = await _fetch_docling_document(document_id)
    footnote_entities = SemanticDocumentAugmentationExportService.extract_footnotes(doc)
    return {"entities": footnote_entities}

@router.get("/headers", response_model=HeadersResponse)
async def get_headers(document_id: str):
    """
    Retrieve all page headers in the document.
    
    Each header (text at the top of a page, such as running titles or chapter names) is returned with text and bounding box.
    """
    doc = await _fetch_docling_document(document_id)
    header_entities = SemanticDocumentAugmentationExportService.extract_headers(doc)
    return {"entities": header_entities}

@router.get("/footers", response_model=FootersResponse)
async def get_footers(document_id: str):
    """
    Retrieve all page footers in the document.
    
    Each footer (text at the bottom of a page, like page numbers or footnotes in the margin) is returned with text and bounding box.
    """
    doc = await _fetch_docling_document(document_id)
    footer_entities = SemanticDocumentAugmentationExportService.extract_footers(doc)
    return {"entities": footer_entities}

@router.get("/lists", response_model=ListsResponse)
async def get_lists(document_id: str):
    """
    Retrieve all lists (bulleted or numbered) from the document.
    
    Each list is returned as a single entity with the combined text of its items and a bounding box covering the list.
    """
    doc = await _fetch_docling_document(document_id)
    list_entities = SemanticDocumentAugmentationExportService.extract_lists(doc)
    return {"entities": list_entities}

@router.get("/algorithms", response_model=AlgorithmsResponse)
async def get_algorithms(document_id: str):
    """
    Retrieve all algorithm/code blocks from the document.
    
    Each code block (monospaced algorithm listing) is returned with its full text and bounding box.
    """
    doc = await _fetch_docling_document(document_id)
    algo_entities = SemanticDocumentAugmentationExportService.extract_algorithms(doc)
    return {"entities": algo_entities}

@router.get("/equations", response_model=EquationsResponse)
async def get_equations(document_id: str):
    """
    Retrieve all block equations (formulas) from the document.
    
    Each equation is returned as LaTeX/text form (if available) along with its bounding box.
    """
    doc = await _fetch_docling_document(document_id)
    equation_entities = SemanticDocumentAugmentationExportService.extract_equations(doc)
    return {"entities": equation_entities}

@router.get("/references", response_model=ReferencesResponse)
async def get_references(document_id: str):
    """
    Retrieve all bibliography/reference entries from the document.
    
    Each reference entry in the bibliography is returned with its text and bounding box.
    """
    doc = await _fetch_docling_document(document_id)
    reference_entities = SemanticDocumentAugmentationExportService.extract_references(doc)
    return {"entities": reference_entities}

# This is a complete document export - definitely should be async with websocket updates
@router.get("/export", response_model=PapermageDocumentResponse)
async def export_papermage_style(
    background_tasks: BackgroundTasks,
    document_id: str
):
    """
    Export the entire document in Papermage-compatible format.
    
    This combines all entity types into a single response, giving a complete representation
    of the document. Useful for applications that expect Papermage format data.
    """
    doc = await _fetch_docling_document(document_id)
    
    # Create empty response structure
    response = PapermageDocumentResponse(
        paragraphs=[],
        sentences=[],
        tokens=[],
        sections=[],
        titles=[],
        authors=[],
        tables=[],
        figures=[],
        captions=[],
        footnotes=[],
        headers=[],
        footers=[],
        lists=[],
        algorithms=[],
        equations=[],
        references=[]
    )
    
    # Start background extraction for all entities
    background_tasks.add_task(
        _export_full_document_background,
        doc, 
        response
    )
    
    return response

@router.get("/export/async", response_model=TaskStatusResponse)
async def export_papermage_style_async(
    orchestrator: Annotated[AsyncLocalOrchestrator, Depends(get_orchestrator)],
    document_id: str
):
    """
    Asynchronously export the entire document in Papermage-compatible format.
    
    Full document export is computationally intensive. This endpoint returns a task ID
    that can be used to poll for results or connect via WebSocket for progress updates.
    """
    # Verify document exists first
    await _fetch_docling_document(document_id)
    
    task = await orchestrator.enqueue(
        request={"operation": "export_papermage", "document_id": document_id}
    )
    task_queue_position = await orchestrator.get_queue_position(task_id=task.task_id)
    return TaskStatusResponse(
        task_id=task.task_id,
        task_status=task.task_status,
        task_position=task_queue_position,
    )

# Background task for complete document export
async def _export_full_document_background(doc, response_obj):
    """Background task to export all document entities"""
    try:
        # Extract each entity type and update the response object
        response_obj.paragraphs = SemanticDocumentAugmentationExportService.extract_paragraphs(doc)
        response_obj.sentences = SemanticDocumentAugmentationExportService.extract_sentences(doc)
        response_obj.tokens = SemanticDocumentAugmentationExportService.extract_tokens(doc)
        response_obj.sections = SemanticDocumentAugmentationExportService.extract_sections(doc)
        response_obj.titles = SemanticDocumentAugmentationExportService.extract_title(doc)
        response_obj.authors = SemanticDocumentAugmentationExportService.extract_authors(doc)
        response_obj.tables = SemanticDocumentAugmentationExportService.extract_tables(doc)
        response_obj.figures = SemanticDocumentAugmentationExportService.extract_figures(doc)
        response_obj.captions = SemanticDocumentAugmentationExportService.extract_captions(doc)
        response_obj.footnotes = SemanticDocumentAugmentationExportService.extract_footnotes(doc)
        response_obj.headers = SemanticDocumentAugmentationExportService.extract_headers(doc)
        response_obj.footers = SemanticDocumentAugmentationExportService.extract_footers(doc)
        response_obj.lists = SemanticDocumentAugmentationExportService.extract_lists(doc)
        response_obj.algorithms = SemanticDocumentAugmentationExportService.extract_algorithms(doc)
        response_obj.equations = SemanticDocumentAugmentationExportService.extract_equations(doc)
        response_obj.references = SemanticDocumentAugmentationExportService.extract_references(doc)
        
        _log.info(f"Full document export completed successfully")
    except Exception as e:
        _log.error(f"Error during full document export: {str(e)}") 