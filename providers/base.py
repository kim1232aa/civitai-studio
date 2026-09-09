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
    def catalog(self, q: str, category: str, status: str, page: int = 1, pageSize: int = 50) -> dict:
        """Return {total, count, items, backend, page, pageSize, hasMore, nextPage, ...}.

        page/pageSize are optional. Providers that only implement (q, category, status)
        still work; the HTTP handler slices that full filtered list.
        """
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

    def cancel_job(self, job_id: str) -> tuple[int, dict]:
        return 400, {"error": f"{self.label} 没有取消接口"}

    def categories(self) -> list:
        return []

    def search_loras(self, q: str, nsfw: bool = True):
        return 200, {"items": [], "backend": self.id, "note": f"{self.label} 没有 LoRA 搜索"}
