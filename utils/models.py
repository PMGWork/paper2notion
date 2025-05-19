from pydantic import BaseModel

class PaperMeta(BaseModel):
    title: str = ""
    authors: str = ""
    journals: str = ""
    year: int = 0
    abstract: str = ""