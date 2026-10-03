from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Every list endpoint returns this."""

    items: list[T]
    total: int
    page: int
    page_size: int
