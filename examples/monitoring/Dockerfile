FROM python:3.6-alpine

ARG APP_DIR=/app
WORKDIR $APP_DIR/

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY config.yaml worker.py $APP_DIR/

CMD python -m aioworkers -c config.yaml --logging info