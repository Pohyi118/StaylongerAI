"""Vercel entrypoint for the StayLongerAI FastAPI application.

Vercel exposes this function at ``/api``. ``vercel.json`` funnels API and
WhatsApp callback paths through that entrypoint while preserving the requested
path in a private query parameter. The adapter restores that path before
FastAPI handles the request.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode

from backend.main import app as _backend_app


class _RewrittenPathAdapter:
    """Restore paths that Vercel rewrites through the single Python function."""

    def __init__(self, application: Any) -> None:
        self._application = application

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") == "http":
            query_string = scope.get("query_string", b"")
            query_pairs = parse_qsl(
                query_string.decode("utf-8", errors="replace"),
                keep_blank_values=True,
            )
            restored_path = next(
                (value for key, value in query_pairs if key == "__staylonger_path"),
                None,
            )

        else:
            query_pairs = []
            restored_path = None

        path = scope.get("path", "")
        if not restored_path and (
            path == "/api/webhook" or path.startswith("/api/webhook/")
        ):
            restored_path = path[4:] or "/"

        if restored_path and restored_path.startswith("/"):
            patched_scope = dict(scope)
            patched_scope["path"] = restored_path
            patched_scope["raw_path"] = restored_path.encode("utf-8")
            patched_scope["query_string"] = urlencode(
                [(key, value) for key, value in query_pairs if key != "__staylonger_path"],
                doseq=True,
            ).encode("utf-8")

            await self._application(patched_scope, receive, send)
            return

        await self._application(scope, receive, send)


app = _RewrittenPathAdapter(_backend_app)
