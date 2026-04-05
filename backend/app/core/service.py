from typing import Generic, TypeVar

T = TypeVar("T")


class BaseService(Generic[T]):
    def __init__(self, repo: T):
        self.repo: T = repo