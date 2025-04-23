# papermage_schemas.py
from pydantic import BaseModel
from typing import List, Optional, Dict

class Box(BaseModel):
    page: int
    x1: float
    y1: float
    x2: float
    y2: float

#Paragraph Schema representation:
class ParagraphEntity(BaseModel):
    text: str
    boxes: List[Box]

class ParagraphsResponse(BaseModel):
    entities: List[ParagraphEntity]

#Sentence Schema representation:
class SentenceEntity(BaseModel):
    text: str
    boxes: List[Box]

class SentencesResponse(BaseModel):
    entities: List[SentenceEntity]

#Token Schema representation:
class TokenEntity(BaseModel):
    text: str
    boxes: List[Box]

class TokensResponse(BaseModel):
    entities: List[TokenEntity]

#Section Schema representation:
class SectionEntity(BaseModel):
    text: str
    boxes: List[Box]

class SectionsResponse(BaseModel):
    entities: List[SectionEntity]

#Title Schema representation:
class TitleEntity(BaseModel):
    text: str
    boxes: List[Box]

class TitlesResponse(BaseModel):
    entities: List[TitleEntity]

#Author Schema representation:
class AuthorEntity(BaseModel):
    text: str
    boxes: List[Box]

class AuthorsResponse(BaseModel):
    entities: List[AuthorEntity]

#Table Schema representation:
class TableEntity(BaseModel):
    text: str        # flattened table text
    boxes: List[Box]

class TablesResponse(BaseModel):
    entities: List[TableEntity]

#Figure Schema representation:
class FigureEntity(BaseModel):
    # Figures may not have text content; we include an optional descriptor
    text: Optional[str] = None 
    boxes: List[Box]

class FiguresResponse(BaseModel):
    entities: List[FigureEntity]

#Caption Schema representation:
class CaptionEntity(BaseModel):
    text: str
    boxes: List[Box]

class CaptionsResponse(BaseModel):
    entities: List[CaptionEntity]

#Footnote Schema representation:
class FootnoteEntity(BaseModel):
    text: str
    boxes: List[Box]

class FootnotesResponse(BaseModel):
    entities: List[FootnoteEntity]

#Header Schema representation:
class HeaderEntity(BaseModel):
    text: str
    boxes: List[Box]

class HeadersResponse(BaseModel):
    entities: List[HeaderEntity]

#Footer Schema representation:
class FooterEntity(BaseModel):
    text: str
    boxes: List[Box]

class FootersResponse(BaseModel):
    entities: List[FooterEntity]

#List Schema representation:
class ListEntity(BaseModel):
    text: str
    boxes: List[Box]

class ListsResponse(BaseModel):
    entities: List[ListEntity]

#Algorithm Schema representation:
class AlgorithmEntity(BaseModel):
    text: str
    boxes: List[Box]

class AlgorithmsResponse(BaseModel):
    entities: List[AlgorithmEntity]

#Equation Schema representation:
class EquationEntity(BaseModel):
    text: str
    boxes: List[Box]

class EquationsResponse(BaseModel):
    entities: List[EquationEntity]

#Reference Schema representation:
class ReferenceEntity(BaseModel):
    text: str
    boxes: List[Box]

class ReferencesResponse(BaseModel):
    entities: List[ReferenceEntity]

#Semantic Document Augmentation Schema representation:
class Span(BaseModel):
    start: int
    end: int

class SemanticDocumentAugmentationEntity(BaseModel):
    spans: List[Span]
    boxes: List[Box]
    # metadata could be added if needed, but we'll omit if empty

class PapermageDocumentResponse(BaseModel):
    symbols: str
    entities: Dict[str, List[SemanticDocumentAugmentationEntity]]













