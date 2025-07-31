"""Type stubs for vectordb package."""

from typing import List, Dict, Any, Optional

class Memory:
    memory: List[Dict[str, Any]]
    memory_file: Optional[str]

    def __init__(
        self,
        memory_file: Optional[str] = None,
        chunking_strategy: dict = ...,
        embeddings: str = "normal",
    ) -> None: ...
    def save(
        self,
        texts: str | List[str],
        metadata_list: Dict[str, Any] | List[Dict[str, Any]],
        memory_file: Optional[str] = None,
    ) -> None: ...
    def search(
        self,
        query: str,
        top_n: int = 5,
        unique: bool = False,
        batch_results: str = "flatten",
    ) -> List[Dict[str, Any]]: ...
    def clear(self) -> None: ...
    def dump(self) -> None: ...
