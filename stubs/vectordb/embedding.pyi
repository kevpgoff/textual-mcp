import abc
from _typeshed import Incomplete
from abc import ABC, abstractmethod

class BaseEmbedder(ABC, metaclass=abc.ABCMeta):
    @abstractmethod
    def embed_text(self, chunks: list[str]) -> list[list[float]]: ...

class Embedder(BaseEmbedder):
    sbert: bool
    model: Incomplete
    def __init__(self, model_name: str = "normal") -> None: ...
    def embed_text(self, chunks: list[str]) -> list[list[float]]: ...
