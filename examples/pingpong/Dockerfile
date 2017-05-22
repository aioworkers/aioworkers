FROM python:3.6-alpine

WORKDIR /worker

RUN apk add --no-cache gcc musl-dev

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY config.yaml app.py docker-entrypoint.sh /worker/

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["--help"]
