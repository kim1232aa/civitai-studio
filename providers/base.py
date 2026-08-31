from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Provider(ABC):
    """One vendor plug-in. Translate studio payload internally; do not share mappers."""

    id: str
    label: str

    @abstractmethod
    def has_key(self) -> bool:
        ...

    @abstractmethod
    def catalog(self, q: str, category: str, status: str) -> dict:
        """Return {total, count, items, backend, ...} with UI catalog keys."""
        ...

    @abstractmethod
    def owns_service(self, service_id: str) -> bool:
        ...

    @abstractmethod
    def owns_job(self, job_id: str) -> bool:
        ...

    @abstractmethod
    def generate(self, payload: dict) -> tuple[int, dict]:
        """Submit a job. Only the HTTP handler may call this after POST /api/generate."""
        ...

    @abstractmethod
    def whatif(self, payload: dict) -> tuple[int, dict]:
        ...

    @abstractmethod
    def job_status(self, job_id: str) -> tuple[int, dict]:
        """On succeeded, attach saved via providers.http.save_media_urls."""
        ...

    def categories(self) -> list:
        return []
