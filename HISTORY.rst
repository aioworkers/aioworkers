=======
History
=======

Development
-----------

* Drop incorrect stubgen (#202)
* Method URI.with_host keep auth (#203)
* Add methods AsyncPath.is_dir/is_file (#205)
* Fix cmd from cython (#210)



0.26 (2023-07-21)
-----------------

* AsyncPath.unlink with missing_ok (#197)
* AsyncPath.rmtree and rmdir (#198)



0.25 (2023-07-19)
-----------------

* Fix option ++groups and add ++group (#192)
* Option --version (#193)
* Improve and fix AsyncPath and add AbstractFileSystem (#195)



0.24.1 (2023-07-10)
-------------------

* Fix using optional formatter and output (#188)


0.24 (2023-07-08)
-----------------

* Improve SocketServer.cleanup (#177)
* Web server support keep-alive (#179)
* Option --config/-c one value on key (#182)
* Option ++group/+g one value on key (#183)
* Cli support --output and --formatter for format results (#186)
* Use name in iter_entry_points (#187)



0.23 (2023-06-20)
-----------------

* Load plugins from entry_points (#165)
* Fix race init for Subprocess (#168)
* Skip start step on run command (#169)
* Use metadata for Updater (#170)
* Use logging option first (#171)



0.22 (2023-06-12)
-----------------

* Support py3.11 (#142)
* Support toml config (#136)
* Detect inactive path in get_object (#144)
* Fix warnings with get_object (#143)
* Config KeyError with full path (#145)
* Separated logger for named signal (#160)
* Add param raises to Context.wait_all (#161)
* Signal raises error (#162)
* Add connect_timeout and sent_start to Context (#163)



0.21.1 (2023-03-20)
-------------------

* Check awaitable for non coro from cython (#127)


0.21 (2022-12-11)
-----------------

* Improve timeout queue (#108, #109)
* Improve Python 3.10 support and drop 3.6 (#103) @rossnomann
* Add utils.random_seed and run on current process
* Use yaml.SafeLoader instead of yaml.Loader
* Context kwargs with instance of Entity (#113)
* ValueExtractor support kwargs (#113)
* Links between entities (#112)



0.20 (2022-01-13)
-----------------

* Drop support Python 3.5
* Add support Python 3.10
* add stubs by stubgen
* URI impl (#85)
* Support run asgi on aioworkers (#86)
* Add default header Date to net.web (#87)
* Decode Content-Type: text/plain
* Default key web.Application is "web" instead of "app" (#88)
* Fix default encode/decode charset
* Add cpus factor for processes
* Fix log for ContextProcessor.ready



0.19.2 (2021-05-19)
-------------------

* Fix match processing key with url
* Fix FileSystemStorage create dir


0.19.1 (2021-05-09)
-------------------

* Revert Cache for ConfigFileLoader


0.19 (2021-05-03)
-----------------

* Support run aioworkers over asgi
* Cache for ConfigFileLoader
* Simple repr(Context) for not interact mode
* Signal logs (#70)
* Support py3.9
* MultiExecutorEntity
* setdefault logging.version
* fix concurrent supervisor.init



0.18 (2020-06-06)
-----------------

* AbstractEntity.__init__ with kwargs (#61)
* fix empty list ListValueMatcher.get_value
* Improve supervisor
* change Supervisor.__call__ & Worker.__call__



0.17 (2020-04-27)
-----------------

* Graceful shutdown
* msgpack & bson formatters



0.16 (2020-04-20)
-----------------

* ValueExtractor with original order
* Improve queue.timeout
* Flag --shutdown-timeout
* [fea] - maintain set_config return value (#58)
* cleanup for DictReader
* improve AsyncPath and AsyncFile



0.15.1 (2019-12-24)
-------------------

* fix StringReplaceLoader.matchers
* aioworkers.net.web without formatting for bytes and str


0.15 (2019-12-18)
-----------------

* BREAKING CHANGES in aioworkers.storage.http.(Ro)Storage
* Impl aioworkers.net.web.client
* AbstractHttpStorage
* Revert Context inhered from AbstractConnector
* LoggingEntity based on AbstractNamedEntity
* AbstractConnector.robust_connect
* AbstractConnector based on LoggingEntity



0.14.9 (2019-12-14)
-------------------

* fix get_bool
* fix ValueExtractor.extractor null without default


0.14.8 (2019-12-08)
-------------------

* cache for plugins


0.14.7 (2019-11-30)
-------------------

* find_iter without self
* fix prompt_toolkit>=3 + aiocontextvars


0.14.6 (2019-11-26)
-------------------

* fix recursive find_iter
* fix Context.__getitem__ for py3.7 & py3.8
* fix asyncgen glob in filesystem storage for py3.7 & py3.8


0.14.5 (2019-11-24)
-------------------

* fix break


0.14.4 (2019-11-23)
-------------------

* Break version
* fix cli multiprocessing
* fix default command
* fix get_bool & replacer `*.ini`


0.14.3 (2019-10-29)
-------------------

* fix cli
* cli as plugin


0.14.2 (2019-10-22)
-------------------

* fix AbstractNestedEntity


0.14.1 (2019-10-21)
-------------------

* fix AbstractConnector groups
* import Crontab in master


0.14 (2019-10-20)
-----------------

* fix Crontab FutureWarning (#12)
* AsyncFile.unlink
* change SocketServer.bind
* fix unconfigured BaseFileSystemStorage repr
* Plugin.parse_known_args
* fix context param for signal
* Context.processes with cleanup
* SocketServer.cleanup



0.13 (2019-06-17)
-----------------

* AbstractConnector (#8)
* new Context signals: connect, disconnect, cleanup
* Chain from formatter registry (#29)
* Improve AbstractNestedEntity
* LoggingEntity
* Config.__repr__
* AbstractSender with smtp sender and proxy
* AbstractFindStorage
* Multiexecute subprocess (#28)
* Add cli param --multiprocessing
* Add SocketServer
* Context.find_iter
* Improve AsyncPath



0.12 (2018-10-20)
-----------------

* Load logging config first (#9)
* Cli option --pid-file
* Extractor env to config (#5)
* Fix interact await func on py37 (#7)
* FileSystemStorage with methods list and length
* Fix log import_name
* Drop default run in Subprocess
* Fix updater
* Plugin aioworkers.net.web



0.11.4 (2018-06-29)
-------------------

* Fix send config to stdin subprocess


0.11.3 (2018-06-23)
-------------------

* Check signature of class entity
* Method Config.load_plugin
* Flag force for search_plugins


0.11.2 (2018-06-13)
-------------------

* Fix unicode README.rst
* Fix init ExecutorEntity


0.11.1 (2018-05-15)
-------------------

* Additional params for get_int, get_float..
* Autoload configs by mask plugin* only for package
* Drop deprecated modules amqp, redis, app


0.11 (2018-05-08)
-----------------

* Config now is immutable
* Config support extendable methods such as get_int, get_float..
* Plugin.configs is sequence of config files of plugin
* Methods set_context and set_config of entities
* label `obj` for config to attach already created entities
* Support run process with ipykernel
* Dropped module aioworkers.config
* Dropped deprecated class aioworkers.http.Application



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
