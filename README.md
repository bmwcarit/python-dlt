# python-dlt

python-dlt is a thin Python ctypes wrapper around libdlt functions. It was
primarily created for use with BMW's test execution framework. However,
the implementation is independent and the API makes few assumptions about
the intended use.

Note: This is only tested with libdlt version v2.18.8 and v2.18.10,
later versions might require adaptations. The package will not support previous libdlt
versions from python-dlt v2.0. Also only GENIVI DLT daemon produced traces
have been tested.

## Design

The code is split up into 3 primary components:

* The `core`: This subpackage provides the major chunk of ctypes wrappers for
  the structures defined in libdlt. It abstracts out the libdlt structures for use
  by the rest of python-dlt. Classes defined here ideally should *not* be used
  outside of python-dlt. The module `core_base.py` provides the default
  implementation of the classes and the other `core_*.py` modules provide the
  overrides for the version specific implementations of libdlt. The correct version
  specific implementation will be loaded automatically at runtime. (the logic for
  this is in `core/__init__.py`)

* The python interface classes: These are defined in `dlt.py`. Most of the
  classes here derive from their corresponding ctypes class definitions from
  `core` and provide a more python friendly api/access to the underlying C/ctypes
  implementations. Ideally, python code using `python-dlt` would use these classes
  rather than the base classes in `core`.

* API for tools: This is the component that provides common interfaces required
  by the tools that use `python-dlt`, like the `DLTBroker`, 'DLTLifecycle' etc. These
  classes do not have equivalents in libdlt and were created based on usage
  requirements (and as such make assumptions about the manner in which they would
  be used).

If you're reading this document to work on the core or the python classes, it
would be a good idea to first understand the design of libdlt itself. This is
fairly well documented (look under the `doc/` directory of the `dlt-deamon` code
base). Of course the best reference is the code itself. `dlt-daemon` is written
in C and is a pretty well laid out, straight forward (ie: not many layers of
abstractions), small code base. Makes for good bedtime reading.

The rest of this document will describe and demonstrate some of the design of
the external API of python-dlt.

The classes most relevant for users of python-dlt possibly are `DLTClient`,
`DLTFile`, `DLTMessage`, `DLTBroker`. The names hopefully make their purpose
evident.

Here are examples of some interesting ways to use these classes:

* DLTFile and DLTMessage::

```python
    >>> from dlt import dlt
    >>> # DLTFile object can be obtained by loading a trace file
    >>> d = dlt.load("high_full_trace.dlt")
    >>> d.generate_index()      # Read the whole trace file and generate its index
    >>> print(d.counter_total)  # number of DLT messages in the file
    ...
    >>> print(d[0])             # messages can be indexed
    ...
    >>> for msg in d:           # DLTFile object is iterable
    ...     print(msg.apid)             # DLTMessage objects have all the attrs
    ...     print(msg.payload_decoded)  # one might expect from a DLT frame
    ...     print(msg)          # The str() of the DLTMessage closely matches the
    ...                         # output of dlt-receive
    >>> d[0] == d[-1]           # DLTMessage objects can be compared to each other
    >>> d.compare(dict(apid="SYS", citd="JOUR")) # ...or can be compared to an
    ...                                          # dict of attributes
    >>> import pickle
    >>> pickle.dumps(d[0])      # DLTMessage objects are (de)serializable using
    ...                         # the pickle protocol (this is to enable sharing
    ...                         # of the DLTMessage in a multiprocessing
    ...                         # environment)
```


* DLTClient and DLTBroker::

```python
    >>> from dlt import dlt
    >>> c = dlt.DLTClient(servIP="127.0.0.1")   # Only initializes the client
    >>> c.connect()                      # ...this connects
    >>> dlt.dltlib.dlt_receiver_receive(ctypes.byref(client.receiver), DLT_RECEIVE_SOCKET)  # receives data
    >>> c.read_message()                 # reads a single DLTMessage from received data  and returns it
    >>>
    >>> # more interesting is the DLTBroker class...
    >>> # - create an instance that initializes a DLTClient. Accepts a filename
    >>> #   where DLT traces would be stored
    >>> broker = DLTBroker(ip_address="127.0.0.1", filename='/tmp/testing_log.dlt')
    >>> # needs to be started and stopped explicitly and will create a run a
    >>> # DLTClient instance in a new *process*.
    >>> broker.start()
    >>> broker.stop()
    >>>
    >>> # Usually, used in conjunction with the DLTContext class from mtee
    >>> from mtee.testing.connectors.connector_dlt import DLTContext
    >>> broker = DLTBroker(ip_address="127.0.0.1", filename="/tmp/testing_log.dlt", verbose=True)
    >>> ctx = DLTContext(broker, filters=[("SYS", "JOUR")])
    >>> broker.start()
    >>> print(ctx.wait_for(count=10))
    >>>
```

## Design of DLTBroker

The DLTBroker abstracts out the management of 2 (multiprocessing) queues:

* The `message_queue`: This queue receives *all* messages from the DLT daemon
  (via a DLTClient instance, running as a separate process, code in
  `dlt.dlt_broker_handlers.DLTMessageHandler`) and stores them to a
  trace file.

* The `filter_queue`: This queue instructs the `DLTMessageHandler` which
  messages would be interesting at runtime, to be filtered and returned (for
  example, via a request from `DLTContext`). This is run as a separate thread in
  the `DLTBroker` process. The code for this is in
  `dlt.dlt_broker_handlers.DLTContextHandler`.

## Running tox on a local machine

In order to run tox command for this repository, please perform the following:

1. Build a docker image from the `Dockerfile` provided using:

```commandline
$ docker build -t python-dlt -f Dockerfile .
```

2. Run the tox in the docker container using:

```commandline
$ docker run -it --rm --volume $(pwd):/workspace python-dlt /bin/sh -xc "tox -e py3,lint"
```

3. [Special Case] Getting an interactive shell inside the docker container to run arbitrary commands:

```commandline
$ docker run -it --rm --volume $(pwd):/workspace --entrypoint sh python-dlt
```
