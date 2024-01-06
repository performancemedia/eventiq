import pytest

from eventiq.asyncapi.v2.generator import get_async_api_spec as get_asyncapi_v2
from eventiq.asyncapi.v3.generator import get_async_api_spec as get_asyncapi_v3


@pytest.mark.parametrize("generator", (get_asyncapi_v2, get_asyncapi_v3))
def test_asyncapi_generation(service, generator):
    spec = generator(service)
    assert spec.info.title == service.title
