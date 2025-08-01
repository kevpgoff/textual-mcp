from typing import Any

MRPT_LOADED: bool

class VectorSearch:
    @staticmethod
    def get_unique_k_elements(i: Any, d: Any, k: int = 15, diverse: bool = False) -> Any: ...
    @staticmethod
    def run_mrpt(vector: Any, vectors: Any, k: int = 15, batch_results: str = "flatten") -> Any: ...
    @staticmethod
    def run_faiss(
        vector: Any, vectors: Any, k: int = 15, batch_results: str = "flatten"
    ) -> Any: ...
    @staticmethod
    def search_vectors(
        query_embedding: list[float],
        embeddings: list[list[float]],
        top_n: int,
        batch_results: str = "flatten",
    ) -> list[tuple[int, float]]: ...
