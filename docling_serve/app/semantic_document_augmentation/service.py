import re
from docling.datamodel.document import DoclingDocument, DocItemLabel, BoundingBox
from typing import List, Dict
from .schemas import Box,Span
import uuid

class SemanticDocumentAugmentationExportService:

    # Store documents in memory for testing purposes
    _document_store: dict[str, DoclingDocument] = {}

    @classmethod
    def register_document(cls, doc: DoclingDocument) -> str:
        doc_id = str(uuid.uuid4())
        cls._document_store[doc_id] = doc
        return doc_id

    @classmethod
    def get_document(cls, doc_id: str) -> DoclingDocument | None:
        return cls._document_store.get(doc_id)

    # Extract paragraphs from the document
    @staticmethod
    def extract_paragraphs(doc: DoclingDocument) -> List[dict]:
        paragraphs = []
        for item in doc.texts:
            if item.label == DocItemLabel.PARAGRAPH or str(item.label) == "paragraph":
                # Get text content
                para_text = item.text
                # Determine page number (assuming each TextItem is confined to one page)
                page_no = SemanticDocumentAugmentationExportService._get_page_number(item, doc)
                # Get bounding box coordinates (convert to top-left origin)
                bbox = item.bbox
                bbox_top_left = bbox.to_top_left_origin() if hasattr(bbox, "to_top_left_origin") else bbox  # ensure top-left coords
                box_coords = Box(
                    page=page_no,
                    x1=bbox_top_left.l, y1=bbox_top_left.t,
                    x2=bbox_top_left.r, y2=bbox_top_left.b
                )
                paragraphs.append({"text": para_text, "boxes": [box_coords]})
        return paragraphs

    # Helper function to get the page number of an item
    @staticmethod
    def _get_page_number(item, doc: DoclingDocument) -> int:
        """Traverse parents to find the page number of this item."""
        node = item
        while node.parent:
            node = node.parent.resolve()  # follow RefItem to actual object
            if hasattr(node, "page_no") and node.page_no is not None:
                return node.page_no
        # Fallback: if not found via parent, maybe the item itself has page_no
        return getattr(item, "page_no", 1)

    # Extract sentences from the document
    @staticmethod
    def extract_sentences(doc: DoclingDocument) -> List[dict]:
        sentences = []
        # Reuse paragraphs from doc (to avoid re-parsing text layout again)
        for para in SemanticDocumentAugmentationExportService.extract_paragraphs(doc):
            para_text = para["text"]
            para_box = para["boxes"][0]
            # Simple sentence splitting (could be enhanced with NLP for better accuracy)
            split_points = [m.end() for m in re.finditer(r'(?<=[\.!?])\s+', para_text)]
            start_idx = 0
            for end_idx in split_points:
                sent_text = para_text[start_idx:end_idx].strip()
                if sent_text:
                    # Approximate the bounding box by using the full paragraph box (since precise per sentence coords not in Docling by default)
                    sentence_box = Box(page=para_box.page, x1=para_box.x1, y1=para_box.y1,
                                       x2=para_box.x2, y2=para_box.y2)
                    sentences.append({"text": sent_text, "boxes": [sentence_box]})
                start_idx = end_idx
            # Last sentence (after final split point)
            last_text = para_text[start_idx:].strip()
            if last_text:
                sentence_box = Box(page=para_box.page, x1=para_box.x1, y1=para_box.y1,
                                   x2=para_box.x2, y2=para_box.y2)
                sentences.append({"text": last_text, "boxes": [sentence_box]})
        return sentences
    
    # Extract tokens from the document
    @staticmethod
    def extract_tokens(doc: DoclingDocument) -> List[dict]:
        tokens = []
        sentences = SemanticDocumentAugmentationExportService.extract_sentences(doc)
        for sent in sentences:
            sent_text = sent["text"]
            sent_box = sent["boxes"][0]
            # Split on whitespace (simple tokenization; could refine to handle punctuation separately)
            raw_tokens = sent_text.split()
            for tok in raw_tokens:
                # If needed, strip punctuation attached to token ends here (optional)
                token_text = tok
                token_box = Box(page=sent_box.page, x1=sent_box.x1, y1=sent_box.y1,
                                x2=sent_box.x2, y2=sent_box.y2)
                tokens.append({"text": token_text, "boxes": [token_box]})
        return tokens  

    # Extract sections from the document
    @staticmethod
    def extract_sections(doc: DoclingDocument) -> List[dict]:
        sections = []
        for item in doc.texts:
            if str(item.label) == "section_header" or item.label == DocItemLabel.SECTION_HEADER:
                sec_text = item.text
                page_no = SemanticDocumentAugmentationExportService._get_page_number(item, doc)
                bbox = item.bbox
                bbox_tl = bbox.to_top_left_origin() if hasattr(bbox, "to_top_left_origin") else bbox
                section_box = Box(page=page_no, x1=bbox_tl.l, y1=bbox_tl.t, x2=bbox_tl.r, y2=bbox_tl.b)
                sections.append({"text": sec_text, "boxes": [section_box]})
        return sections

    # Extract titles from the document
    @staticmethod
    def extract_title(doc: DoclingDocument) -> List[dict]:
        titles = []
        for item in doc.texts:
            if str(item.label) == "title" or item.label == DocItemLabel.TITLE:
                title_text = item.text
                page_no = SemanticDocumentAugmentationExportService._get_page_number(item, doc)
                bbox = item.bbox
                bbox_tl = bbox.to_top_left_origin() if hasattr(bbox, "to_top_left_origin") else bbox
                title_box = Box(page=page_no, x1=bbox_tl.l, y1=bbox_tl.t, x2=bbox_tl.r, y2=bbox_tl.b)
                titles.append({"text": title_text, "boxes": [title_box]})
                break  # assume only one title
        return titles

    # Extract authors from the document
    @staticmethod
    def extract_authors(doc: DoclingDocument) -> List[dict]:
        authors = []
        title_items = SemanticDocumentAugmentationExportService.extract_title(doc)
        if not title_items:
            return authors
        title_page = title_items[0]["boxes"][0].page
        title_bbox_bottom = title_items[0]["boxes"][0].y2
        # Gather text items on the same page, immediately below the title
        for item in doc.texts:
            page_no = SemanticDocumentAugmentationExportService._get_page_number(item, doc)
            if page_no == title_page:
                bbox = item.bbox
                bbox_tl = bbox.to_top_left_origin() if hasattr(bbox, "to_top_left_origin") else bbox
                if bbox_tl.t > title_bbox_bottom:  # appears below title
                    if str(item.label) not in ("section_header", "title") and len(item.text) < 100:
                        # Heuristic: treat short text below title as author line
                        author_text = item.text
                        author_box = Box(page=page_no, x1=bbox_tl.l, y1=bbox_tl.t, x2=bbox_tl.r, y2=bbox_tl.b)
                        authors.append({"text": author_text, "boxes": [author_box]})
        return authors

    # Extract tables from the document
    @staticmethod
    def extract_tables(doc: DoclingDocument) -> List[dict]:
        tables = []
        for table in doc.tables:
            # Flatten table text: iterate rows and cells
            flat_text_lines = []
            if table.data:
                for row in table.data.grid:
                    cell_texts = [cell.text.strip() if cell.text else "" for cell in row]
                    flat_text_lines.append("\t".join(cell_texts))
            flat_text = "\n".join(flat_text_lines)
            # Table bounding box (either directly or computed from cells)
            if hasattr(table, "bbox") and table.bbox:
                bbox = table.bbox
            else:
                # compute from cells if needed
                cell_bboxes = [cell.bbox for cell in table.data.table_cells if cell.bbox]
                bbox = BoundingBox.enclosing_bbox(cell_bboxes) if cell_bboxes else None
            if bbox:
                bbox_tl = bbox.to_top_left_origin() if hasattr(bbox, "to_top_left_origin") else bbox
                page_no = SemanticDocumentAugmentationExportService._get_page_number(table, doc)
                table_box = Box(page=page_no, x1=bbox_tl.l, y1=bbox_tl.t, x2=bbox_tl.r, y2=bbox_tl.b)
            else:
                # If no bbox (should not happen typically), skip coordinates
                table_box = None
            entity = {"text": flat_text}
            if table_box:
                entity["boxes"] = [table_box]
            else:
                entity["boxes"] = []
            tables.append(entity)
        return tables

    # Extract figures from the document
    @staticmethod
    def extract_figures(doc: DoclingDocument) -> List[dict]:
        figures = []
        for pic in doc.pictures:
            # We won't have textual content for figures. Provide a placeholder or None.
            fig_text = None
            # Determine bounding box of figure
            if hasattr(pic, "bbox") and pic.bbox:
                bbox = pic.bbox
            else:
                # PictureItem might not have bbox directly; perhaps derive from image size & position
                bbox = getattr(pic, "image", None)
                if bbox and hasattr(bbox, "bbox"):
                    bbox = bbox.bbox
            if bbox:
                bbox_tl = bbox.to_top_left_origin() if hasattr(bbox, "to_top_left_origin") else bbox
                page_no = SemanticDocumentAugmentationExportService._get_page_number(pic, doc)
                fig_box = Box(page=page_no, x1=bbox_tl.l, y1=bbox_tl.t, x2=bbox_tl.r, y2=bbox_tl.b)
            else:
                fig_box = None
            entity = {"text": fig_text}
            entity["boxes"] = [fig_box] if fig_box else []
            figures.append(entity)
        return figures

    # Extract captions from the document
    @staticmethod
    def extract_captions(doc: DoclingDocument) -> List[dict]:
        captions = []
        for item in doc.texts:
            if str(item.label) == "caption" or item.label == DocItemLabel.CAPTION:
                cap_text = item.text
                page_no = SemanticDocumentAugmentationExportService._get_page_number(item, doc)
                bbox = item.bbox
                bbox_tl = bbox.to_top_left_origin() if hasattr(bbox, "to_top_left_origin") else bbox
                cap_box = Box(page=page_no, x1=bbox_tl.l, y1=bbox_tl.t, x2=bbox_tl.r, y2=bbox_tl.b)
                captions.append({"text": cap_text, "boxes": [cap_box]})
        return captions

    # Extract footnotes from the document
    @staticmethod
    def extract_footnotes(doc: DoclingDocument) -> List[dict]:
        footnotes = []
        for item in doc.texts:
            if str(item.label) == "footnote" or item.label == DocItemLabel.FOOTNOTE:
                fn_text = item.text
                page_no = SemanticDocumentAugmentationExportService._get_page_number(item, doc)
                bbox = item.bbox
                bbox_tl = bbox.to_top_left_origin() if hasattr(bbox, "to_top_left_origin") else bbox
                fn_box = Box(page=page_no, x1=bbox_tl.l, y1=bbox_tl.t, x2=bbox_tl.r, y2=bbox_tl.b)
                footnotes.append({"text": fn_text, "boxes": [fn_box]})
        return footnotes

    # Extract headers from the document
    @staticmethod
    def extract_headers(doc: DoclingDocument) -> List[dict]:
        headers = []
        for item in doc.texts:
            if str(item.label) == "page_header" or item.label == DocItemLabel.PAGE_HEADER:
                hd_text = item.text
                page_no = SemanticDocumentAugmentationExportService._get_page_number(item, doc)
                bbox = item.bbox
                bbox_tl = bbox.to_top_left_origin() if hasattr(bbox, "to_top_left_origin") else bbox
                hd_box = Box(page=page_no, x1=bbox_tl.l, y1=bbox_tl.t, x2=bbox_tl.r, y2=bbox_tl.b)
                headers.append({"text": hd_text, "boxes": [hd_box]})
        return headers

    # Extract footers from the document
    @staticmethod
    def extract_footers(doc: DoclingDocument) -> List[dict]:
        footers = []
        for item in doc.texts:
            if str(item.label) == "page_footer" or item.label == DocItemLabel.PAGE_FOOTER:
                ft_text = item.text
                page_no = SemanticDocumentAugmentationExportService._get_page_number(item, doc)
                bbox = item.bbox
                bbox_tl = bbox.to_top_left_origin() if hasattr(bbox, "to_top_left_origin") else bbox
                ft_box = Box(page=page_no, x1=bbox_tl.l, y1=bbox_tl.t, x2=bbox_tl.r, y2=bbox_tl.b)
                footers.append({"text": ft_text, "boxes": [ft_box]})
        return footers

    # Extract lists from the document
    @staticmethod
    def extract_lists(doc: DoclingDocument) -> List[dict]:
        lists = []
        for group in getattr(doc, "groups", []):
            if not hasattr(group, "group_label"):
                continue
            label = str(group.group_label) if hasattr(group, "group_label") else None
            if label in ("list", "ordered_list", "List", "OrderedList"):
                # Resolve child references to actual list item objects
                items_texts = []
                item_bboxes = []
                for child_ref in group.children:
                    child = child_ref.resolve()
                    if hasattr(child, "text"):
                        items_texts.append(child.text)
                    if hasattr(child, "bbox") and child.bbox:
                        bbox = child.bbox
                        bbox_tl = bbox.to_top_left_origin() if hasattr(bbox, "to_top_left_origin") else bbox
                        item_bboxes.append(bbox_tl)
                list_text = "\n".join(items_texts)
                if item_bboxes:
                    # compute overall bounding box covering all item boxes
                    all_bbox = BoundingBox.enclosing_bbox(item_bboxes)
                    page_no = SemanticDocumentAugmentationExportService._get_page_number(child, doc)
                    list_box = Box(page=page_no, x1=all_bbox.l, y1=all_bbox.t, x2=all_bbox.r, y2=all_bbox.b)
                else:
                    list_box = None
                entity = {"text": list_text, "boxes": [list_box] if list_box else []}
                lists.append(entity)
        return lists

    # Extract algorithms from the document
    @staticmethod
    def extract_algorithms(doc: DoclingDocument) -> List[dict]:
        algorithms = []
        temp_buffer = []
        temp_box_list = []
        last_y2 = None
        for item in doc.texts:
            if str(item.label) == "code" or item.label == DocItemLabel.CODE:
                # If multiple code items are contiguous, combine them
                bbox = item.bbox
                bbox_tl = bbox.to_top_left_origin() if hasattr(bbox, "to_top_left_origin") else bbox
                if last_y2 is not None and bbox_tl.t - last_y2 < 20:  # if this code item starts right after previous (threshold)
                    # Continue the current code block
                    temp_buffer.append(item.text)
                    temp_box_list.append(bbox_tl)
                    last_y2 = bbox_tl.b
                else:
                    # Flush previous if exists
                    if temp_buffer:
                        combined_text = "\n".join(temp_buffer)
                        combined_bbox = BoundingBox.enclosing_bbox(temp_box_list)
                        page_no = SemanticDocumentAugmentationExportService._get_page_number(item, doc)
                        algo_box = Box(page=page_no, x1=combined_bbox.l, y1=combined_bbox.t,
                                       x2=combined_bbox.r, y2=combined_bbox.b)
                        algorithms.append({"text": combined_text, "boxes": [algo_box]})
                    # Start new buffer
                    temp_buffer = [item.text]
                    temp_box_list = [bbox_tl]
                    last_y2 = bbox_tl.b
        # Append any remaining buffer
        if temp_buffer:
            combined_text = "\n".join(temp_buffer)
            combined_bbox = BoundingBox.enclosing_bbox(temp_box_list)
            page_no = SemanticDocumentAugmentationExportService._get_page_number(item, doc)
            algo_box = Box(page=page_no, x1=combined_bbox.l, y1=combined_bbox.t,
                           x2=combined_bbox.r, y2=combined_bbox.b)
            algorithms.append({"text": combined_text, "boxes": [algo_box]})
        return algorithms

    # Extract equations from the document
    @staticmethod
    def extract_equations(doc: DoclingDocument) -> List[dict]:
        equations = []
        for item in doc.texts:
            if str(item.label) == "formula" or item.label == DocItemLabel.FORMULA:
                eq_text = item.text
                page_no = SemanticDocumentAugmentationExportService._get_page_number(item, doc)
                bbox = item.bbox
                bbox_tl = bbox.to_top_left_origin() if hasattr(bbox, "to_top_left_origin") else bbox
                eq_box = Box(page=page_no, x1=bbox_tl.l, y1=bbox_tl.t, x2=bbox_tl.r, y2=bbox_tl.b)
                equations.append({"text": eq_text, "boxes": [eq_box]})
        return equations

    # Extract references from the document
    @staticmethod
    def extract_references(doc: DoclingDocument) -> List[dict]:
        references = []
        for item in doc.texts:
            if str(item.label) == "reference" or item.label == DocItemLabel.REFERENCE:
                ref_text = item.text
                page_no = SemanticDocumentAugmentationExportService._get_page_number(item, doc)
                bbox = item.bbox
                bbox_tl = bbox.to_top_left_origin() if hasattr(bbox, "to_top_left_origin") else bbox
                ref_box = Box(page=page_no, x1=bbox_tl.l, y1=bbox_tl.t, x2=bbox_tl.r, y2=bbox_tl.b)
                references.append({"text": ref_text, "boxes": [ref_box]})
        return references

    # Export the entire document in Papermage-style JSON structure, with symbols and layered entities.
    @staticmethod
    def export_document(doc: DoclingDocument) -> dict:
        """
        Export the entire document in Papermage-style JSON structure, with symbols and layered entities.
        """
        # 1. Build the symbols string and record spans for each base text item
        symbols_list = []
        current_index = 0
        item_spans: Dict[str, tuple] = {}  # mapping from item (by self_ref or id) to (start, end)
        # Traverse doc.body tree in order
        def traverse(node):
            nonlocal current_index
            for child_ref in node.children:
                child = child_ref.resolve()
                # If child is a Group (like section or list), recurse
                if hasattr(child, "children") and getattr(child, "children", None):
                    traverse(child)
                # If child is a TextItem or similar content item with text
                if hasattr(child, "text") and child.text:
                    text = child.text
                    start_idx = current_index
                    symbols_list.append(text)
                    current_index += len(text)
                    # Add a newline or space after certain items to mimic natural separation
                    if str(child.label) in ("paragraph", "section_header", "list_item", "footnote", "reference"):
                        symbols_list.append("\n")
                        current_index += 1
                    # Record span (excluding the added newline)
                    end_idx = start_idx + len(text)
                    item_spans[child.self_ref] = (start_idx, end_idx)
        traverse(doc.body)
        symbols_str = "".join(symbols_list)
        # 2. Prepare entity layers
        layers = {}
        # Paragraphs layer
        layers["paragraphs"] = []
        for para in SemanticDocumentAugmentationExportService.extract_paragraphs(doc):
            # Find the original item corresponding to this paragraph (we can match by text and label, or ideally by self_ref if we stored it)
            # Assuming unique text or positions, we do a search in item_spans
            for item in doc.texts:
                if (str(item.label) == "paragraph" or item.label == DocItemLabel.PARAGRAPH) and item.text == para["text"]:
                    span_start, span_end = item_spans.get(item.self_ref, (None, None))
                    if span_start is not None:
                        span = Span(start=span_start, end=span_end)
                        layers["paragraphs"].append({"spans": [span], "boxes": para["boxes"]})
                    break
        # Repeat similarly for other layers:
        layers["sections"] = []
        for sec in SemanticDocumentAugmentationExportService.extract_sections(doc):
            for item in doc.texts:
                if (str(item.label) == "section_header" or item.label == DocItemLabel.SECTION_HEADER) and item.text == sec["text"]:
                    span_start, span_end = item_spans.get(item.self_ref, (None, None))
                    if span_start is not None:
                        span = Span(start=span_start, end=span_end)
                        layers["sections"].append({"spans": [span], "boxes": sec["boxes"]})
                    break
        # ... (Analogous code for titles, authors, footnotes, headers, footers, references using item_spans lookup) ...
        # For sentences and tokens (derived layers), compute spans relative to paragraphs:
        layers["sentences"] = []
        sentence_entities = SemanticDocumentAugmentationExportService.extract_sentences(doc)
        for sent in sentence_entities:
            # find the paragraph in which this sentence belongs
            # simplest: find sent.text in symbols_str and use first match that falls within a paragraph span
            idx = symbols_str.find(sent["text"])
            if idx != -1:
                span = Span(start=idx, end=idx + len(sent["text"]))
                layers["sentences"].append({"spans": [span], "boxes": sent["boxes"]})
        layers["tokens"] = []
        token_entities = SemanticDocumentAugmentationExportService.extract_tokens(doc)
        for tok in token_entities:
            idx = symbols_str.find(tok["text"])
            if idx != -1:
                span = Span(start=idx, end=idx + len(tok["text"]))
                layers["tokens"].append({"spans": [span], "boxes": tok["boxes"]})
        # Tables:
        layers["tables"] = []
        for table in SemanticDocumentAugmentationExportService.extract_tables(doc):
            # We won't find the flattened table text in symbols (we did not insert it into symbols_str),
            # so we give an empty span or skip spans for tables since their text isn't in symbols continuous flow.
            layers["tables"].append({"spans": [], "boxes": table["boxes"]})
        # Figures:
        layers["figures"] = []
        for fig in SemanticDocumentAugmentationExportService.extract_figures(doc):
            layers["figures"].append({"spans": [], "boxes": fig["boxes"]})
        # Captions:
        layers["captions"] = []
        for cap in SemanticDocumentAugmentationExportService.extract_captions(doc):
            # find caption text in symbols
            idx = symbols_str.find(cap["text"])
            if idx != -1:
                span = Span(start=idx, end=idx + len(cap["text"]))
                layers["captions"].append({"spans": [span], "boxes": cap["boxes"]})
        # Footnotes, headers, footers, references are similar to captions:
        layers["footnotes"] = []
        for fn in SemanticDocumentAugmentationExportService.extract_footnotes(doc):
            idx = symbols_str.find(fn["text"])
            if idx != -1:
                span = Span(start=idx, end=idx + len(fn["text"]))
                layers["footnotes"].append({"spans": [span], "boxes": fn["boxes"]})
        layers["headers"] = []
        for hd in SemanticDocumentAugmentationExportService.extract_headers(doc):
            idx = symbols_str.find(hd["text"])
            if idx != -1:
                span = Span(start=idx, end=idx + len(hd["text"]))
                layers["headers"].append({"spans": [span], "boxes": hd["boxes"]})
        layers["footers"] = []
        for ft in SemanticDocumentAugmentationExportService.extract_footers(doc):
            idx = symbols_str.find(ft["text"])
            if idx != -1:
                span = Span(start=idx, end=idx + len(ft["text"]))
                layers["footers"].append({"spans": [span], "boxes": ft["boxes"]})
        # Lists:
        layers["lists"] = []
        for lst in SemanticDocumentAugmentationExportService.extract_lists(doc):
            # lists' combined text may not be exactly in symbols if list items were separated by newlines which we included.
            # But since we inserted list items text and newline in symbols when traversing, the combined text likely appears.
            idx = symbols_str.find(lst["text"].split("\n")[0])
            # If found the first item, we can span from first to last item's span
            if idx != -1:
                end_idx = idx + len(lst["text"])
                layers["lists"].append({"spans": [Span(start=idx, end=end_idx)], "boxes": lst["boxes"]})
        # Algorithms:
        layers["algorithms"] = []
        for alg in SemanticDocumentAugmentationExportService.extract_algorithms(doc):
            idx = symbols_str.find(alg["text"].split("\n")[0])
            if idx != -1:
                end_idx = idx + len(alg["text"])
                layers["algorithms"].append({"spans": [Span(start=idx, end=end_idx)], "boxes": alg["boxes"]})
        # Equations:
        layers["equations"] = []
        for eq in SemanticDocumentAugmentationExportService.extract_equations(doc):
            idx = symbols_str.find(eq["text"])
            if idx != -1:
                span = Span(start=idx, end=idx + len(eq["text"]))
                layers["equations"].append({"spans": [span], "boxes": eq["boxes"]})
        # References:
        layers["references"] = []
        for ref in SemanticDocumentAugmentationExportService.extract_references(doc):
            idx = symbols_str.find(ref["text"])
            if idx != -1:
                span = Span(start=idx, end=idx + len(ref["text"]))
                layers["references"].append({"spans": [span], "boxes": ref["boxes"]})
        return {"symbols": symbols_str, "entities": layers}








