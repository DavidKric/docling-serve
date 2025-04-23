# papermage_routes.py
from fastapi import APIRouter, HTTPException, Depends
from .schemas import ParagraphsResponse, SentencesResponse, TokensResponse, SectionsResponse, TitlesResponse, AuthorsResponse, TablesResponse, FiguresResponse, CaptionsResponse, FootnotesResponse, HeadersResponse, FootersResponse, ListsResponse, AlgorithmsResponse, EquationsResponse, ReferencesResponse, PapermageDocumentResponse
from .service import SemanticDocumentAugmentationExportService

router = APIRouter(prefix="/semantic-document-augmentation")

@router.get("/paragraphs", response_model=ParagraphsResponse)
async def get_paragraphs(document_id: str):
    """
    Retrieve all paragraphs from the document as Papermage-style entities.
    
    Each paragraph is returned with its full text and bounding box coordinates on the page, 
    analogous to Papermage's text block segmentation (paragraphs).
    """
    doc = _fetch_docling_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    para_entities = SemanticDocumentAugmentationExportService.extract_paragraphs(doc)
    return {"entities": para_entities}

@router.get("/sentences", response_model=SentencesResponse)
async def get_sentences(document_id: str):
    """
    Retrieve all sentences from the document in Papermage-style format.
    
    Splits paragraphs into sentences using punctuation heuristics. Each sentence 
    is returned with its text and an approximate bounding box.
    """
    doc = _fetch_docling_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    sentence_entities = SemanticDocumentAugmentationExportService.extract_sentences(doc)
    return {"entities": sentence_entities}

@router.get("/tokens", response_model=TokensResponse)
async def get_tokens(document_id: str):
    """
    Retrieve all tokens (words and symbols) from the document in Papermage-style format.
    
    Each token is provided with the token text and an approximate bounding box. This is analogous 
    to Papermage's token layer, though precise coordinates may be approximated.
    """
    doc = _fetch_docling_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    token_entities = SemanticDocumentAugmentationExportService.extract_tokens(doc)
    return {"entities": token_entities}

@router.get("/sections", response_model=SectionsResponse)
async def get_sections(document_id: str):
    """
    Retrieve the section headings of the document.
    
    Each section (e.g., a major heading in the document) is returned with its heading text and location,
    analogous to Papermage's section entities.
    """
    doc = _fetch_docling_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    section_entities = PapermageExportService.extract_sections(doc)
    return {"entities": section_entities}

@router.get("/titles", response_model=TitlesResponse)
async def get_titles(document_id: str):
    """
    Retrieve the document title in Papermage-style format.
    
    Returns the title text of the document with its bounding box. In most cases, this is the main heading on the first page.
    """
    doc = _fetch_docling_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    title_entities = PapermageExportService.extract_title(doc)
    return {"entities": title_entities}

@router.get("/authors", response_model=AuthorsResponse)
async def get_authors(document_id: str):
    """
    Retrieve the document authors in Papermage-style format.
    
    Attempts to identify author lines (usually immediately below the title on the first page). 
    Each author entry (or the whole author line) is returned with text and bounding box.
    """
    doc = _fetch_docling_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    author_entities = PapermageExportService.extract_authors(doc)
    return {"entities": author_entities}

@router.get("/tables", response_model=TablesResponse)
async def get_tables(document_id: str):
    """
    Retrieve all tables in the document in Papermage-style format.
    
    Each table is returned with a flattened text representation of its contents and its bounding box on the page.
    """
    doc = _fetch_docling_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    table_entities = SemanticDocumentAugmentationExportService.extract_tables(doc)
    return {"entities": table_entities}

@router.get("/figures", response_model=FiguresResponse)
async def get_figures(document_id: str):
    """
    Retrieve all figures (images) from the document in Papermage-style format.
    
    Each figure is represented by its bounding box. (No textual content is included for figures.)
    """
    doc = _fetch_docling_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    figure_entities = SemanticDocumentAugmentationExportService.extract_figures(doc)
    return {"entities": figure_entities}

@router.get("/captions", response_model=CaptionsResponse)
async def get_captions(document_id: str):
    """
    Retrieve all figure and table captions in the document.
    
    Each caption (figure or table description text) is returned with its text content and bounding box.
    """
    doc = _fetch_docling_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    caption_entities = SemanticDocumentAugmentationExportService.extract_captions(doc)
    return {"entities": caption_entities}

@router.get("/footnotes", response_model=FootnotesResponse)
async def get_footnotes(document_id: str):
    """
    Retrieve all footnotes from the document.
    
    Each footnote is returned with its text content and bounding box (typically at the bottom of a page).
    """
    doc = _fetch_docling_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    footnote_entities = SemanticDocumentAugmentationExportService.extract_footnotes(doc)
    return {"entities": footnote_entities}

@router.get("/headers", response_model=HeadersResponse)
async def get_headers(document_id: str):
    """
    Retrieve all page headers in the document.
    
    Each header (text at the top of a page, such as running titles or chapter names) is returned with text and bounding box.
    """
    doc = _fetch_docling_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    header_entities = SemanticDocumentAugmentationExportService.extract_headers(doc)
    return {"entities": header_entities}

@router.get("/footers", response_model=FootersResponse)
async def get_footers(document_id: str):
    """
    Retrieve all page footers in the document.
    
    Each footer (text at the bottom of a page, like page numbers or footnotes in the margin) is returned with text and bounding box.
    """
    doc = _fetch_docling_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    footer_entities = SemanticDocumentAugmentationExportService.extract_footers(doc)
    return {"entities": footer_entities}

@router.get("/lists", response_model=ListsResponse)
async def get_lists(document_id: str):
    """
    Retrieve all lists (bulleted or numbered) from the document.
    
    Each list is returned as a single entity with the combined text of its items and a bounding box covering the list.
    """
    doc = _fetch_docling_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    list_entities = SemanticDocumentAugmentationExportService.extract_lists(doc)
    return {"entities": list_entities}

@router.get("/algorithms", response_model=AlgorithmsResponse)
async def get_algorithms(document_id: str):
    """
    Retrieve all algorithm/code blocks from the document.
    
    Each code block (monospaced algorithm listing) is returned with its full text and bounding box.
    """
    doc = _fetch_docling_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    algo_entities = SemanticDocumentAugmentationExportService.extract_algorithms(doc)
    return {"entities": algo_entities}

@router.get("/equations", response_model=EquationsResponse)
async def get_equations(document_id: str):
    """
    Retrieve all block equations (formulas) from the document.
    
    Each equation is returned as LaTeX/text form (if available) along with its bounding box.
    """
    doc = _fetch_docling_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    equation_entities = SemanticDocumentAugmentationExportService.extract_equations(doc)
    return {"entities": equation_entities}

# papermage_routes.py (continued)
@router.get("/references", response_model=ReferencesResponse)
async def get_references(document_id: str):
    """
    Retrieve all bibliography/reference entries from the document.
    
    Each reference entry in the bibliography is returned with its text and bounding box.
    """
    doc = _fetch_docling_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    reference_entities = SemanticDocumentAugmentationExportService.extract_references(doc)
    return {"entities": reference_entities}

@router.get("/export", response_model=PapermageDocumentResponse)
async def export_papermage_style(document_id: str):
    """
    Export the entire document in Papermage-style JSON format.
    
    This returns a JSON with a 'symbols' string of the whole document text and an 'entities' 
    mapping where each key is a layer (paragraphs, sentences, tokens, sections, etc.) 
    and the value is a list of entities with spans into the symbols and bounding boxes, 
    analogous to Papermage's Document JSON.
    """
    doc = _fetch_docling_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    papermage_doc = SemanticDocumentAugmentationExportService.export_document(doc)
    return papermage_doc





