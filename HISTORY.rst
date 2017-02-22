=======
History
=======

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
