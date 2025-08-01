"""Type stubs for mistletoe markdown parser."""

from typing import List as ListType, Any

class Document:
    """Root document token."""

    def __init__(self, text: str) -> None: ...

    children: ListType[Any]
