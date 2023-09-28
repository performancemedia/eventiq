FROM python:3.9.2-slim

RUN pip install 'eventiq[commons, nats]'

COPY ./service.py ./service

CMD ['eventiq', 'run', 'service:service']