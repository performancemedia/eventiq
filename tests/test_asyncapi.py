from eventiq.asyncapi.v2.generator import get_async_api_spec


def test_asyncapi_generation(service):
    spec = get_async_api_spec(service)
    assert spec.info.title == service.title
