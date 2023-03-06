## Encoders

::: eventiq.types.Encoder
    handler: python
    options:
      show_root_heading: true
      show_source: false
      members:
        - CONTENT_TYPE
        - encode
        - decode

::: eventiq.encoders.json.JsonEncoder
    handler: python
    options:
      show_root_heading: true
      show_source: true

::: eventiq.encoders.orjson.OrjsonEncoder
    handler: python
    options:
      show_root_heading: true
      show_source: true

::: eventiq.encoders.msgpack.MsgPackEncoder
    handler: python
    options:
      show_root_heading: true
      show_source: true

::: eventiq.encoders.pickle.PickleEncoder
    handler: python
    options:
      show_root_heading: true
      show_source: true
