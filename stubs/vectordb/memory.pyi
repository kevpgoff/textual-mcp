from .chunking import Chunker as Chunker
from .embedding import BaseEmbedder as BaseEmbedder, Embedder as Embedder
from .storage import Storage as Storage
from .vector_search import VectorSearch as VectorSearch
from _typeshed import Incomplete
from typing import Any

class Memory:
    memory_file: Incomplete
    memory: Incomplete
    metadata_memory: Incomplete
    chunker: Incomplete
    metadata_index_counter: int
    text_index_counter: int
    embedder: Incomplete
    vector_search: Incomplete
    def __init__(
        self,
        memory_file: str | None = None,
        chunking_strategy: dict[Any, Any] | None = None,
        embeddings: BaseEmbedder | str = "normal",
    ) -> None: ...
    def save(
        self,
        texts: Any,
        metadata: list[Any] | list[dict[str, Any]] | None = None,
        memory_file: str | None = None,
    ) -> None: ...
    def search(
        self, query: str, top_n: int = 5, unique: bool = False, batch_results: str = "flatten"
    ) -> list[dict[str, Any]]: ...
    def clear(self) -> None: ...
    def dump(self) -> None: ...
