async def test_consumer_process(test_consumer, ce):
    res = await test_consumer.process(ce)
    assert res == 42
