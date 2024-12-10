import pytest
from urls import TEST_URLS

from onshape_api.connect import Client
from onshape_api.models.document import Document
from onshape_api.parse import get_instances, get_instances_sync

DOCUMENTS = [Document.from_url(url) for url in TEST_URLS]


@pytest.fixture(scope="module")
def documents() -> list[Document]:
    return DOCUMENTS


@pytest.fixture(scope="module")
def client() -> Client:
    return Client()


@pytest.mark.parametrize("document", DOCUMENTS)
def test_example(document):
    assert isinstance(document, Document)


@pytest.mark.parametrize("document", DOCUMENTS)
def test_get_instances(document: Document, client: Client):
    assembly = client.get_assembly(
        did=document.did,
        wtype=document.wtype,
        wid=document.wid,
        eid=document.eid,
    )

    async_instances, async_occurrences, async_id_to_name_map = get_instances(assembly)
    sync_instances, sync_occurrences, sync_id_to_name_map = get_instances_sync(assembly)

    assert len(async_instances) == len(sync_instances)
    assert len(async_occurrences) == len(sync_occurrences)
    assert len(async_id_to_name_map) == len(sync_id_to_name_map)

    assert async_instances == sync_instances
    assert async_occurrences == sync_occurrences
    assert async_id_to_name_map == sync_id_to_name_map
