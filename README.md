WSGI v2.0
=========

THIS IS EXPERIMENTAL WORK.

Initial work on a WSGI v2.0 specification. Will include a reference
implementation and tests.

To Specify, or not to Specify
-----------------------------

There is obviously a balance between providing a small complete specification
and providing the core features that are common to a large majority of
application code. As a test of whether a feature should be part of this
specification I propose the following question, "Can this be implemented as a
middleware?" I believe that if a feature can be implemented as middleware we
should avoid specifying it, and instead rely on convention and community
consensus.

An example of a good feature idea that would be best left to middleware are
the logging facilities introduced by Rack. They provide "log.error",
"log.critical", (etc..) keys in the environ to provide a standardized method
for application logging. This feature could be implemented strictly as a
middleware, and hence does not belong in this specification.


The WSGI Interface
==================

In a nutshell, this specification revolves around a simple method for handling
HTTP requests and generating HTTP responses. The basic application is a simple
callable that accepts a single parameter that describes the request and returns
a three-tuple that describes the response. All values referred to in this
document are assumed to be the most direct equivalent for a given interpreter.


A Simple Example
----------------

CPython 2.5::

    def application(environ):
        status = "200 OK"
        headers = [("Content-Type", "text/plain")]
        body = "Hello, world!\n"
        return status, headers, [body]

CPython 3.1::

    def application(environ):
        status = b"200 OK"
        headers = [(b"Content-Type", b"text/plain")]
        body = b"Hello, world!\n"
        return status, headers, [body]

Obviously, variable names are not part of the specification. The current names
are only used to be illustrative of their intent and to have a common name
by which we can refer to them.

.. note::

    CPython 2.6 and 2.7 should be able to use either format because of the
    following condtion::

        >>> type(b"") is type("")

The environ dict
----------------

The environ should provide a complete description of the HTTP request. A
fundamental goal should be to provide WSGI applications the ability to produce
a semantically equivalent request. For instance, in WSGI 1.0 there was no
standardized way to access the original request URI before irreversible
mutations (%HH escape decoding for instance). This is an example of following
the CGI spec that should be avoided in the new specification.

Along with providing a description of the HTTP request, the environ should
also provide the capability to pass along data that is out-of-band to the
HTTP protocol. For instance, information regarding the server (port, hostname,
ip), information regarding the client (ip, port, etc), and information
regarding the execution environment (multithreading, multiprocessing).

Keys in the environ dict should be considered metadata about a given
request. As such, they are not part of the request or the response. Since they
are clearly not I/O related, they should be the default character type for
the given interpreter. Ie, whatever type a bare string literal defaults to.
This prevents the need for all code using an environ to have to worry about
the key type.

Deciding whether a key should be part of the requirements for adherence to this
specification should follow the same criteria for deciding what should be a
feature. Each key should be required to correctly interpret an HTTP request or
provide information that would not otherwise be detectable by application
code.


HTTP Related
++++++++++++

All HTTP values must be raw byte values. These values are pulled off a socket
and may end up being sent to another socket. Unfortunately, HTTP predates much
of the push for character encodings. Some may point that it specifies using
latin-1 encoding in most places but I would argue that people do weird
things with HTTP. As much as I would love to take a hardline on encodings, I
am unable to justify specifying latin-1 when clients may ignore this and some
application developers will be expected to handle such bad clients.

  * http.method - Request method (bytes)

  * http.uri.raw - The original unmodified request URI. (bytes)
  
  * http.uri.path - The path part of the request URI. (bytes)
  
  * http.uri.query_string - The query string part of the request URI (bytes)
  
  * http.version - The HTTP protocol version specified in the request.
    (two-tuple of integers)
  
  * http.headers - A dict of lists. keys are header names. Values are lists
    of header values. Most often these lists will have a length of one, but
    HTTP specifies that headers can be repeated. As such our representation
    should reflect this fact. (keys are bytes, values are lists of bytes)
  
  * http.trailers - A dict of lists. Keys are trailer names and values are
    lists of trailer values. (keys are bytes, values are lists of bytes)
  
  * http.body - A readable stream that provides any data that was sent with
    the request. This stream *must* respect the HTTP protocol in the data
    it provides. For instance, it must respect content-length, transfer-
    encoding, and request protocol version. (readable stream)


OOB Related
+++++++++++

This set of keys deals with information that an application requires from the
server that cannot be derived from the request.

  * wsgi.version - The tuple (2, 0) if the server complies with this
    specification.

  * wsgi.url_scheme - The original URL scheme used to make this request so
    applications can generate correct links to other resources it controls.
    Should generally be "http" or "https". (bytes)

  * wsgi.script_name - Servers invoking a WSGI application often reserve a
    section of its URI path hierarchy for request dispatching. Ie, if a server
    is hosting two WSGI applications, one application my get requests that have
    a paths matching "/foo.*" while the other application may get requests
    matching "/bar.*". "wsgi.script_nmae" can be used to inform the application
    of this path information so that it can generate URLs that will be
    compatible with differing path configurations. (bytes)

  * wsgi.multithread - If the application must handle running in an execution
    environment where application code may be called simultaneously from
    multiple threads. (True or False)

  * wsgi.multiprocess - An indication if the application must handle running
    in an execution environment where application code may be called
    simultaneously from multiple processes. (True or False)

  * wsgi.errors - A stream available for application logging. (ie, it must
    be writable). (Writable stream)

  * wsgi.upgrade - A callable that returns an object that represents the raw
    socket connection. This mechanism will replace the start_response callable
    and allow applications to remove the current request from the normal HTTP
    processing loop. (callable that takes no parameters and returns an upgrade
    stream)

  * wsgi.upgraded - A callable that returns a boolean specifying if the
    connection has been upgraded or not. This should be used by middleware
    that create responses (ie, error handling middleware) to determine if
    the exception should be intercepted. If this returns True, the exception
    should be re-raised so that the server can log the error and clean up
    the connection.

  * conn.server_name - They name of the server that the application may wish
    to provide to the application. If there is a "Host" header in the HTTP
    request, this should reflect that value. (bytes)

  * conn.server_port - The port of the socket that the server is listening
    on. If the Host header is present with a specified port, this value
    should reflect that. (int)

  * conn.remote_ip - The IP address of the remote HTTP client. (bytes)
  
  * conn.remote_port - The port of the remote HTTP client. (int)


Encoding Related
++++++++++++++++

To allow applications to dictate how they want various byte types decoded
there are a set of environ key/value pairs that should be respected when
retrieving values from the environ.

  * enc.default - A tuple that specifies the default encoding and error
    type as native strings. The default is ("latin-1", "strict")

[ed: I plan on hashing this out more, but my current thought is to allow people
to specify something like "enc.http.*" which would affect all environ bytes
values with environ keys starting with "http.*". Though this is funny for
things like headers and trailers that are complex values as well as when you
may want to specify the encoding of a specific header or header value (Cookies
being the motivating edge case for that). Maybe a callable that decodes the
value? Something like that. Its time for beer.]


The "http.body" Readable Stream
+++++++++++++++++++++++++++++++

The body readable stream must support the following methods:

  * read(size) - Returns up to size bytes from the request body. If size is
    negative or None, it returns all remaining bytes in the request body. This
    may return fewer bytes than requested if there are not enough bytes left
    in the request body to satisfy the request. When zero bytes remain in
    the request body, this function should return an empty string. All values
    returned from this function must be of the bytes type specified by the
    current interpreter. No character decoding should be applied.

  * readline(size) - Provides the same semantics as read(size) but will also
    limit the data returned to the next newline "\n" character in the request
    body. Unlike WSGI v1.0, the size parameter is requierd to be supported.
    When no more data remains, the empty byte object should be returned.
  
  * readlines([size]) - Return all remaining lines in the request body as a
    list of byte objects. The optional size argument is only specified so that
    the body object matches the built-in file object API. When no more bytes
    are left in the request body, the empty bytes object should be returned.
  
  * __iter__() - Should yield all strings remaining in the request body. When
    no more data exists in the request body, an iterator that yields zero
    values should be returned.

Server implementations must not allow calling code to break the HTTP protocol
by by reading beyond the end of the request body when using this stream object.

Server implementations do not need to implement the ability to rewind request
bodies in any form.

[note: Should I specify a readchunk() method that returns a two-tuple of a
size and iterable for reading requests that were sent with a chunked transfer-
encoding so that apps can proxy chunked requests nearly exactly? Theoretically
an HTTP endpoint that relies on the semantics of such things is mis-behaving,
but its a possibility of specing something out of the realm of possibility.
Granted, most HTTP parsers do not support chunk length parameters, which
probably should not be in this spec.]


The "wsgi.errors" Writable Stream
+++++++++++++++++++++++++++++++++

This error stream is intended for use in a logging system. It must support
enough of the file API to be used with the standard library `logging` module.

  * write(value) - Write the byte represented by value to the stream.
  
  * writelines(seq) - Iterate over `seq` writing each yieled bytes value
    to the underlying stream.
  
  * flush() - Ensure that any data has been sent through to the underlying
    stream. It is possible that this is a no-op depending on implementation. It
    should merely allow applications to ensure that some data has been logged.


The "upgrade" Stream
++++++++++++++++++++

This stream is a readable and writable stream that can be used for direct
communication with the client. It is returned from a call to "wsgi.upgrade"
and should support the following methods:

  * recv(size) - Retrieve at most size bytes from the underlying connection.
    If size is not specified, negative, or None, it should return any available
    data or block until data becomes available.
  
  * send(value) - Send the bytes object value to the client immediately. The
    server should not attempt to buffer data. Servers should be careful to
    comply with this condition even if they are using TCP options like
    TCP_CORK or TCP_NOPUSH.
  
  * sendall(data) - Send all bytes in data? Should I smush this with send?
  
  * makefile() - Should I specify this?
  
  * setblocking() - Should I specify this?


Application Use of Streams
++++++++++++++++++++++++++

Only the methods specified in this document are allowed to be called by any
application code regardless of what the actual object provides. For instance,
if one of the streams has a close() call, it *must* not be called by any
application.


The "wsgi.upgrade" Callable
---------------------------

The "wsgi.upgrade" callable must take zero parameters and return an object
that represents the underlying client connection. This will provide
applications the ability to continue using the "push" paradigm that the old
write(data) callable returned from start_response() provided. Although, in
this case the application becomes responsible for the entire response and must
format its own status message and headers before sending its response.

This extra burden allows developers to use the same mechanics to support actual
HTTP connection upgrades to other protocols if they so desire. For example,
this is necessary to support WebSocket connections.

Once the "wsgi.upgrade" callable has been invoked, the server *must not*
attempt to send any other data to the client. If they application invokes
the upgrade callable and returns True, the server may optionally attempt to
continue reading HTTP requests from the connection. If False is returned the
server *must* close the underlying socket connection.


The HTTP Response
=================

The basic HTTP response returned by a WSGI application must be a three-tuple
containing a status code, a list of headers, and an iterable that represents
the respones body.


Status Code
-----------

That staus code should be a byte object that represents an HTTP status code
and the associated status message. This should match the regular expression:
r"^[1-9]\d\d[ ]+[A-Za-z][A-Za-z ]+$".


Response Headers
----------------

The response headers must be a list of two-tuples. Each two-tuple must
be a pair of byte objects that specify the name and value of the header. If
header values span multiple lines, the application code is repsonisble for
ensuring that the continuation indentation is properly specified. A server
may enforce some constraints on header data, but this is not a requirement.


Response Body
-------------

The respones body returned from an application should be an iterable that
yields byte objects that will be forwarded to the client.


Server Handling of the Response
-------------------------------

A server should not attempt to send any data to a client until the first value
is accessed from the iterator. This will allow for the maximum amount of time
to be able to report any errors.

Once the server starts sending data it will not be possible to recover the
connection. In this situation the server should close the client connection
and report the error out of band in a server log or via some other
implementation defined manner.

A WSGI server should attempt to ensure that the HTTP response complies with
the HTTP protocol. For instance, if an application returns an response
description that contains no Content-Length or Transfer-Encoding, the server
should send the response and then close the underlying client connection to
indicate the end of the response. A WSGI server should not attempt to modify
the response in any way as this is the responsibility of middleware.


Error Handling
--------------

Now that there is no start_response() callable, the method for error handling
has changed. If an application raises an exception while handling a request,
the server should attempt to inform the HTTP client of this error. Generally
this is accomplished using a simple "500 Internal Server Error" response
status. If the server does send such a message it should be very careful to
not send too much information. For instance, the Python traceback should not
be included by default (although, it may be included in a "debug" mode). This
is to prevent too much information leakage to possibly nefarious clients.

A server should also consider whether a request has been partially sent to the
client when handling errors. If a request has already been started and no
error message can be sent, the server should close terminate the current
response and underlying connection and then notify the application developer
with some other out of band communication (ie, a server error log). A
connection that has been upgraded should be considered as started (regardless
if any data has been sent to the client [ed: double check on this caveat]).


Guidelines for Middleware
=========================

When an application is preparing a response it is likely and common that it
will call a second application as part of this processing. Applications that
defer to sub-applications are known as "middleware". Common uses of middleware
include routing, response compression, authentication, or session management.

All middlware must obey they requirements of the server (minus the prohibition
on request/respones modifications) as well as requirements of applications
(accepting an environ parameter, returning a three-tuple).


Common HTTP Behaviors
=====================

This is a list of common HTTP behavior that needs to be addressed by WSGI
servers and applications.


Expect: 100-Continue
--------------------

WSGI servers should automatically handle the "Expect: 100-Continue" header
transparently as it is responsible for direct socket access and thus the best
place to handle this logic. There are three valid methods for handling this
behavior listed below in order from best to worst:

  * When an application attempts to read data from the client, send the
    "HTTP/1.1 100 Continue\r\n\r\n" response before reading data.

  * Immediately send the "HTTP/1.1 100 Continue\r\n\r\n" response before
    invoking the WSGI application

  * Do nothing and wait for the client to timeout and send the body on its own.
    This is very undesirable because the client may wait many seconds before
    timing out.


Trailers
--------

If a request has trailers these should be placed into the "http.trailers"
environ value when they become available.

There may be better ways to deal with this. I have considered specifying
a function on the "http.body" stream that is "read_headers" that will read
the rest of the response to get to the headers if there are any. Before
writing too much code for it I am waiting for feedback.


Notes
-----

  * CGI compliance is not good enough. Most of the complaints I have seen
    revolve around the lack of HTTP compliance.

  * The major motivation for decision making should be to give applications the
    ability to have complete control of the HTTP protocol. The WSGI spec should
    merely serve to provide a standardized interface to the interaction to
    decouple server and app code.

  * The original outline of a function that creates an HTTP response given
    a description of the request has proven to be popular.

  * Other languages implementing WSGI inspired systems have universally done
    away with the start_response callable. This is a good idea as it reduces
    the complexity of the specification substantially.

  * Character encoding issues are a pain in the rear. The WSGI spec is not the
    place to make a decision on this issue because it is application specific.
    Although, specifying a standard way to access various parts of the request
    may provide recommendations on character decoding.

  * The keys in an environ dict should be considered metadata that point at
    subsections of the request. It was a mistake to have HTTP_$(HEADER_NAME)
    semantics as this blurs the line between data and metadata.

  * The original specification made a good decision in limiting the
    spec to only using builtin types. This simplifies the implementation
    greatly for other interpreters and implementations using the C-API.

