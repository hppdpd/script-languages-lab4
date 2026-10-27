from abc import ABC, abstractmethod

from lab4.domain import Laureate


class NotFoundError(Exception):
    """Запис не знайдено."""


class ConflictError(Exception):
    """Порушення унікальності або посилання на неіснуючий запис."""


class LaureateRepository(ABC):
    @abstractmethod
    def list_all(self, limit: int, offset: int) -> list[Laureate]: ...

    @abstractmethod
    def get(self, laureate_id: int) -> Laureate: ...

    @abstractmethod
    def create(self, laureate: Laureate) -> Laureate: ...

    @abstractmethod
    def update(self, laureate_id: int, laureate: Laureate) -> Laureate: ...

    @abstractmethod
    def delete(self, laureate_id: int) -> None: ...
