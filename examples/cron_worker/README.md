# Example of a worker which use a cron schedule 

A simple worker that prints "Done" to the console each minute.


Build it:

```bash
docker build -t cron_worker .
```

Run it:

```bash
docker run -d --rm --name cron_worker_1 cron_worker
```

Check the logs:

```bash
docker logs --follow cron_worker_1
```

Stop worker:

```bash
docker stop cron_worker_1
```