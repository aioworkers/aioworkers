FROM python:3.6-alpine

WORKDIR /worker

RUN apk add --no-cache gcc musl-dev

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY config.yaml worker.py app.py /worker/

CMD python -m aioworkers.cli -c config.yaml -l info