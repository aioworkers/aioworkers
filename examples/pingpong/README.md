# Ping-Pong

This example shows communication between two workers via Redis queries.

## Run

To run this example you need to install Redis.

```bash
cd ping/
python -m aioworkers.cli -c config.yaml -l info
```

```bash
cd pong/
python -m aioworkers.cli -c config.yaml -l info
```

## Docker

Build images:

```bash
docker-compose build
```

Run services:

```bash
docker-compose up
```