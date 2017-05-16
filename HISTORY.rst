=======
History
=======

0.5.0 (2017-05-17)
------------------

* Grouping
* FieldStorageMixin
* Logging level instead root logger level in params cli
* find-links param in PipUpdater
* Open csv in init coro DictReader queue


0.4.5 (2017-04-13)
------------------

* Atomic set in FileSystemStorage
* Correct default crontab in updater

0.4.4 (2017-04-12)
------------------

* BaseUpdater
* Example PingPong

0.4.3 (2017-04-10)
------------------

* FileSystemStorage fix for windows

0.4.2 (2017-04-05)
------------------

* FileSystemStorage method wait free space
* Module humanize
* Example of a cron worker

0.4.1 (2017-03-23)
------------------

* Context access optimization
* Logging cli parameter to specify log level for root logger
* Validate config param and load from io object
* Interact await function
* Fix aiohttp 2.0 import


0.4.0 (2017-03-12)
------------------

* Added ScoreQueue interface
* Implements ScoreQueue in TimestampQueue and RedisZQueue
* Lock refactor with catch aioredis.PoolClosedError
* Added interact mode in cli power by ipython
* Added amqp queue power by asynqp
* Explicity setup signals to stop
* Crontab rule in worker
* Fix stopped mistake in worker
* Fix merge MergeDict and subclass dict


0.3.3 (2017-02-22)
------------------

* Refactor http storage
* RedisStorage based on AbstractListedStorage


0.3.2 (2017-02-20)
------------------

* StorageError in method set http storage


0.3.1 (2017-02-18)
------------------

* Fix redis script in TimestampZQueue


0.3.0 (2017-02-17)
------------------

* Added FutureStorage
* Added TimestampZQueue on redis
* Added Subprocess and Supervisor workers
* Added method copy and move for Storage
* Propagate file extension in HashFileSystemStorage
* Added method to AbstractStorage raw_key
* Cli refactor
* Added counter in Worker
* Used app startup and shutdown signals
* Contains for MergeDict
* Base Queue maxsize optional


0.2.0 (2016-12-05)
------------------

* Added Worker and TimestampQueue
* Added classes queue and storage worked over redis
* Added Formatter and used one in FileSystemStorage and redis classes
* Changes in Context
* Fixed HttpStorage and used yarl.URL

0.1.0 (2016-11-25)
------------------

* Added entities loader
* Added abstract storage
* Fixed configuration
* Changes in BaseApplication

0.0.1 (2016-11-13)
------------------

* Subsystem loading config
* Base application and cli
* Base queue and csv.DictReader
