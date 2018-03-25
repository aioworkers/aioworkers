=======
History
=======

0.10.2 (2018-03-25)
-------------------

* MergeDict supported uri as key
* Catch ProcessLookupError on Subprocess.stop


0.10.1 (2018-02-28)
-------------------

* Improved Subprocess (aioworkers param)
* Fix cli.main with args


0.10.0 (2018-02-22)
-------------------

* Improved Subprocess
* Access member of entity over context
* Proxy queue for readline from stdin
* Command line param --config-stdin


0.9.3 (2017-12-22)
------------------

* Fix FileSystemStorage.get_free_space
* Improve import_name


0.9.2 (2017-12-17)
------------------

* Fix access to nested element
* Improve import_name


0.9.1 (2017-12-11)
------------------

* Fix config loader ini


0.9.0 (2017-12-11)
------------------

* Application is a regular entity not required in context
* Fix load config from http resource
* Search config in plugin by mask plugin.*
* Extends info about fail import in import_name


0.8.0 (2017-11-17)
------------------

* Added AsyncPath based on PurePath
* FileSystemStorage.raw_key -> AsyncPath (backward incompatible)
* FileSystemStorage support nested interface
* Fix Worker.init with uninitialized queue
* Humanize func parse_size & parse_duration
* Prevent branching when accessing private attributes for nested obj
* Move AbstractReader & AbstractWriter to core
* Fix GroupResolver to resolve exclude many groups


0.7.0 (2017-11-04)
------------------

* Plug-in formatters and config_loaders
* Added ChainFormatter for specify pipeline
* cli support url for config
* ZlibFormatter + LzmaFormatter
* AbstractNestedEntity
* Supervisor with queue for children
* Identifying the problem at the start of a worker
* Mark deprecated modules


0.6.2 (2017-10-12)
------------------

* Added support plugins
* HttpStorage support timeout and not checks status with return_status
* Method HttpStorage.reset_session to session_params
* Fixed interactive mode
* Added docs articles


0.6.1 (2017-09-24)
------------------

* Improved HttpStorage and FileSystemStorage
* Added example `monitoring <examples/monitoring>`_ with graphite
* Fix match negative number in ini config
* Calling a worker launches a coro


0.6.0 (2017-06-27)
------------------

* Added commands param in cli
* Added classes for ContextProcessor and FileLoader family
* Context now contextmanager


0.5.1 (2017-06-09)
------------------

* Change grouping cli params (no backward compatibility)
* Add cwd in sys.path with cli
* Auto execution `func` & add utils.module_path


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
