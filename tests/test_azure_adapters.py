import asyncio

import pytest

from orqmesh import AzureBlobStore, AzureContentUnderstandingAdapter, AzureCosmosRepository


class FakeBlobDownload:
    async def readall(self):
        return b"synthetic document"


class FakeBlobClient:
    async def download_blob(self):
        return FakeBlobDownload()


class FakeBlobServiceClient:
    def get_blob_client(self, container, blob):
        self.location = (container, blob)
        return FakeBlobClient()


def test_azure_blob_store_reads_bytes_through_injected_async_client():
    client = FakeBlobServiceClient()
    store = AzureBlobStore(client)

    result = asyncio.run(store.read_bytes("documents", "sample.pdf"))

    assert result == b"synthetic document"
    assert client.location == ("documents", "sample.pdf")


class FakeCosmosContainer:
    async def upsert_item(self, body):
        return body

    def query_items(self, query, parameters=None, **kwargs):
        async def rows():
            yield {"id": "record-1", "partition": kwargs.get("partition_key", "default")}

        return rows()


def test_azure_cosmos_repository_upserts_and_queries_json_documents():
    repository = AzureCosmosRepository(FakeCosmosContainer())

    async def exercise():
        saved = await repository.upsert({"id": "record-1", "value": 10})
        rows = await repository.query(
            "SELECT * FROM c WHERE c.id = @id",
            [{"name": "@id", "value": "record-1"}],
            partition_key="team",
        )
        return saved, rows

    saved, rows = asyncio.run(exercise())
    assert saved["id"] == "record-1"
    assert rows == [{"id": "record-1", "partition": "team"}]


class FakePoller:
    def result(self):
        return FakeCUResult()


class FakeCUResult:
    def as_dict(self):
        return {"status": "succeeded", "fields": {"total": 100}}


class FakeContentUnderstandingClient:
    def begin_analyze_binary(self, analyzer_id, binary_data, content_type):
        self.request = (analyzer_id, binary_data, content_type)
        return FakePoller()


def test_content_understanding_adapter_offloads_blocking_poller():
    client = FakeContentUnderstandingClient()
    adapter = AzureContentUnderstandingAdapter(client)

    result = asyncio.run(adapter.analyze_bytes("document-v1", b"pdf", "application/pdf"))

    assert result["status"] == "succeeded"
    assert client.request == ("document-v1", b"pdf", "application/pdf")


def test_content_understanding_rejects_empty_document():
    adapter = AzureContentUnderstandingAdapter(FakeContentUnderstandingClient())

    with pytest.raises(ValueError, match="content must not be empty"):
        asyncio.run(adapter.analyze_bytes("document-v1", b"", "application/pdf"))