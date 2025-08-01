"""Type stubs for mistletoe block tokens."""

from typing import Any, Optional, List as ListType

__all__ = ["BlockToken", "Heading", "Paragraph", "CodeFence", "BlockCode", "List"]

class BlockToken:
    """Base class for block tokens."""

    children: ListType[Any]
    content: str

class Heading(BlockToken):
    """Heading block token."""

    level: int

class Paragraph(BlockToken):
    """Paragraph block token."""

    pass

class CodeFence(BlockToken):
    """Code fence block token."""

    children: ListType[Any]
    language: str

    def __getitem__(self, index: int) -> Any: ...

class BlockCode(BlockToken):
    """Block code token."""

    children: ListType[Any]

    def __getitem__(self, index: int) -> Any: ...

class List(BlockToken):  # noqa: A001
    """List block token."""

    children: ListType[Any]
    loose: bool
    start: Optional[int]

    def __getitem__(self, index: int) -> Any: ...
