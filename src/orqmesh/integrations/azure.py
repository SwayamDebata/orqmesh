"""Thin async Azure service adapters with application-owned client lifecycle.

Azure SDK packages are intentionally not imported here. Applications construct
and authenticate SDK clients, then inject them into these adapters. This keeps
the core package installable without Azure dependencies and avoids persisting
credentials or client objects in workflow state.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping, Sequence
from typing import Protocol, cast

from orqmesh.models import JSONMapping


class _BlobDownload(Protocol):
    async def readall(self) -> bytes: ...


class _AsyncBlobClient(Protocol):
    async def download_blob(self) -> _BlobDownload: ...


class _AsyncBlobServiceClient(Protocol):
    def get_blob_client(self, container: str, blob: str) -> _AsyncBlobClient: ...


class AzureBlobStore:
    """Read blob contents using an injected ``azure.storage.blob.aio`` client."""

    def __init__(self, client: _AsyncBlobServiceClient) -> None:
        self._client = client

    async def read_bytes(self, container: str, blob: str) -> bytes:
        """Download one blob fully into memory and return its bytes."""
        if not container.strip() or not blob.strip():
            raise ValueError("container and blob must be non-empty")
        downloader = await self._client.get_blob_client(container, blob).download_blob()
        return await downloader.readall()


class _AsyncCosmosContainer(Protocol):
    async def upsert_item(self, body: JSONMapping) -> JSONMapping: ...

    def query_items(
        self,
        query: str,
        parameters: Sequence[JSONMapping] | None = None,
        **kwargs: object,
    ) -> AsyncIterator[JSONMapping]: ...


class AzureCosmosRepository:
    """Small repository adapter around an injected async Cosmos container."""

    def __init__(self, container: _AsyncCosmosContainer) -> None:
        self._container = container

    async def upsert(self, document: JSONMapping) -> JSONMapping:
        """Upsert a JSON-compatible document into the configured container."""
        result = await self._container.upsert_item(body=document)
        if not isinstance(result, Mapping):
            raise TypeError("Cosmos upsert_item must return a mapping")
        return cast(JSONMapping, dict(result))

    async def query(
        self,
        query: str,
        parameters: Sequence[JSONMapping] | None = None,
        *,
        partition_key: str | None = None,
    ) -> list[JSONMapping]:
        """Execute a parameterized query and collect its JSON-like result rows."""
        if not query.strip():
            raise ValueError("query must be non-empty")
        kwargs: dict[str, object] = {}
        if partition_key is not None:
            kwargs["partition_key"] = partition_key
        rows: list[JSONMapping] = []
        async for row in self._container.query_items(query, parameters, **kwargs):
            if not isinstance(row, Mapping):
                raise TypeError("Cosmos query rows must be mappings")
            rows.append(cast(JSONMapping, dict(row)))
        return rows


class _ContentUnderstandingPoller(Protocol):
    def result(self) -> object: ...


class _ContentUnderstandingClient(Protocol):
    def begin_analyze_binary(
        self, analyzer_id: str, binary_data: bytes, content_type: str
    ) -> _ContentUnderstandingPoller: ...


class AzureContentUnderstandingAdapter:
    """Call Azure AI Content Understanding without blocking the event loop.

    The SDK's poller API is synchronous, so both submission and result waiting
    run in worker threads. Client creation, credentials, endpoint configuration,
    retry policy, timeout policy, and client disposal remain with the caller.
    """

    def __init__(self, client: _ContentUnderstandingClient) -> None:
        self._client = client

    async def analyze_bytes(
        self, analyzer_id: str, content: bytes, content_type: str
    ) -> JSONMapping:
        """Submit bytes to an analyzer and return its mapping-shaped result."""
        if not analyzer_id.strip():
            raise ValueError("analyzer_id must be non-empty")
        if not content:
            raise ValueError("content must not be empty")
        if not content_type.strip():
            raise ValueError("content_type must be non-empty")

        poller = await asyncio.to_thread(
            self._client.begin_analyze_binary,
            analyzer_id,
            content,
            content_type,
        )
        result = await asyncio.to_thread(poller.result)
        as_dict = getattr(result, "as_dict", None)
        if callable(as_dict):
            result = await asyncio.to_thread(as_dict)
        if not isinstance(result, Mapping):
            raise TypeError("Content Understanding result must be a mapping")
        return cast(JSONMapping, dict(result))