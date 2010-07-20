PEP: XXX
Title: Python Web Server Gateway Interface v2.0
Version: $Revision$
Last-Modified: $Date$
Author: Phillip J. Eby <pje@telecommunity.com>,
        Paul Joseph Davis <paul.joseph.davis@gmail.com>
Discussions-To: Python Web-SIG <web-sig@python.org>
Status: Draft
Type: Informational
Content-Type: text/x-rst
Created: 07-Dec-2003
Post-History: 07-Dec-2003, 08-Aug-2004, 20-Aug-2004, 27-Aug-2004


Abstract
========

This document specifies a proposed standard interface between web
servers and Python web applications or frameworks, to promote web
application portability across a variety of web servers.


Rationale and Goals
===================

Version 1.0 of the Python Web Server Gateway Interface (WSGI) [1]_ has
over twenty five independent server implementations [2]_ and more than
twenty compatible web frameworks [3]_. The original specification was
so popular that it has been adapted for at least three other programming
languages: Perl [4]_, Ruby [5]_, and JavaScript [6]_.

The original specification was published over seven years ago. Web
development has progressed quite far since that time as well as
development of the Python language. Since the original specification
was published we've seen seven major releases of Python, including
the recent development fork of Python 3K. Python 2.7 has been released
which is the final production release of the Python 2.x development
branch.

To ensure that WSGI adoption can continue as painlessly as possible
on the Python 3K branch there are a few issues that need to be resolved.
There are also a few lingering ambiguities that have been covered in
the original specification that would benefit from a final resolution.

As noted in the original WSGI specification, the cost of implementation
must be minimized so that developers do not need to make a large
investment to support it. Making this a priority has had a very obvious
affect on the adoption rate of the specification, so much so that
other languages have successfully adopted it. Take that Java Servlet
API!

The current updates are motivated by ensuring that the specification
can be implemented on both of the major Python development branches as
well as updating the specification to become more modern with respect
to current crop of web server gateway interfaces. To this end, there
is not much concern for backwards compatibility.

As in the original WSGI specification, there is no prescription for
high level features or deployment strategies. There have been a number
of various common methods for various aspects of deployment or middleware
solutions for a given featuer, but there is no clear winner in any
category that deserves embodiment in the current version of this
specification.

Specification Overview
======================

The WSGI specification is in essence the description of a very simple
callable. This callable accepts a description of a web request and returns
a description of the response. The elegance of this approach is that
these callables can be made easily combined to provide for very powerful
web request processing.


WSGI Applications
-----------------

A WSGI application is a callable that conforms to this specification. The
application can be any type of callable such as a function, method, or
instance with a ``__call__`` method. [ed: Not sure if classes will be able
to support the 3-tuple return value.] Any software that invokes as WSGI
application **must not** depend on the type of callable.

A complete WSGI application may look like this::

    def simple_app(environ):
        """Simplest possible application object"""
        return (200, [(b'Content-Type', b'text/plain')], [b'Hello, World!'])

Or as an instance with a configurable content-type::

    class AppClass(object):
        def __init__(self, ctype):
            self.status = 200
            self.headers = [(b'Content-Type', ctype.encode("latin-1"))]
            self.response = b'Hello, World'

        def __call__(self, environ):
            return (self.status, self.headers, [self.response])

    other_app = AppClass("text/plain")


WSGI Server
-----------

The WSGI server is responsible for invoking an application callable once
for each HTTP request it receives and forwarding the applications response
back to the HTTP client. This example assumes the server is capable of
creating an object that represents the parsed HTTP request.

::

    Write code here!


WSGI Middleware
---------------

Middleware is mere an application that may call another application
but has the ability to modify the request sent to the application
or the returned response. Some common examples of middleware are:

* Routing a request to different application objects based on the
  target URL, after rewriting the ``environ`` accordingly.

* Content postprocessing such as applying XSL stylesheets.

* Session management based on HTTP cookies or other client
  identification.

* Autentication/Authorization for accessing application resources.

Middleware should be transparent to the server that invokes it and
mostly transparent to the application it invokes. Because middleware
is invoked by a server and subsequently invokes an application callable
it is required to abide by the specification for both the server and
application objects.

Here is a simple middleware that captures stack traces and provides
a response that can be used to debug the underlying issue::

    import traceback

    class ErrorReporter(object):
        def __init__(self, app):
            self.app = app

        def __call__(self, environ):
            try:
                return self.app(environ)
            except Exception:
                stack = traceback.format_exc().encode("ascii", "ignore")
                if environ['wsgi.active']():
                    return (500, [(b'Content-Type', b'text/plain')], [stack])
                else:
                    environ['wsgi.errors'].write(stack)

    # Using the middleware with an application
    import my_app
    app = ErrorReporter(my_app.app)


Specification Details
=====================

The ``environ`` argument

An application object must accept a single positional argument. For the
purpose of illustration in this specification it is named ``environ``
but this is obvious not a requirement. This ``environ`` parameter **must**
be an instance of the builtin ``dict`` type. Servers **must** invoke
the application object using a single positional (not keyword) argument.
(E.g. by calling ``result = application(environ)`` as shown above.)



The ``environ`` parameter is a dictionary object, containing CGI-style
environment variables.  This object **must** be a builtin Python
dictionary (*not* a subclass, ``UserDict`` or other dictionary
emulation), and the application is allowed to modify the dictionary
in any way it desires.  The dictionary must also include certain
WSGI-required variables (described in a later section), and may
also include server-specific extension variables, named according
to a convention that will be described below.

The ``start_response`` parameter is a callable accepting two
required positional arguments, and one optional argument.  For the sake
of illustration, we have named these arguments ``status``,
``response_headers``, and ``exc_info``, but they are not required to
have these names, and the application **must** invoke the
``start_response`` callable using positional arguments (e.g.
``start_response(status,response_headers)``).

The ``status`` parameter is a status string of the form
``"999 Message here"``, and ``response_headers`` is a list of 
``(header_name,header_value)`` tuples describing the HTTP response
header.  The optional ``exc_info`` parameter is described below in the
sections on `The start_response() Callable`_ and `Error Handling`_.
It is used only when the application has trapped an error and is
attempting to display an error message to the browser.

The ``start_response`` callable must return a ``write(body_data)``
callable that takes one positional parameter: a string to be written 
as part of the HTTP response body.  (Note: the ``write()`` callable is
provided only to support certain existing frameworks' imperative output
APIs; it should not be used by new applications or frameworks if it
can be avoided.  See the `Buffering and Streaming`_ section for more
details.)

When called by the server, the application object must return an 
iterable yielding zero or more strings.  This can be accomplished in a
variety of ways, such as by returning a list of strings, or by the
application being a generator function that yields strings, or
by the application being a class whose instances are iterable.
Regardless of how it is accomplished, the application object must
always return an iterable yielding zero or more strings.

The server or gateway must transmit the yielded strings to the client 
in an unbuffered fashion, completing the transmission of each string 
before requesting another one.  (In other words, applications
**should** perform their own buffering.  See the `Buffering and 
Streaming`_ section below for more on how application output must be
handled.)

The server or gateway should treat the yielded strings as binary byte
sequences: in particular, it should ensure that line endings are
not altered.  The application is responsible for ensuring that the
string(s) to be written are in a format suitable for the client.  (The
server or gateway **may** apply HTTP transfer encodings, or perform
other transformations for the purpose of implementing HTTP features
such as byte-range transmission.  See `Other HTTP Features`_, below,
for more details.)

If a call to ``len(iterable)`` succeeds, the server must be able 
to rely on the result being accurate.  That is, if the iterable 
returned by the application provides a working ``__len__()`` 
method, it **must** return an accurate result.  (See
the `Handling the Content-Length Header`_ section for information
on how this would normally be used.)

If the iterable returned by the application has a ``close()`` method,
the server or gateway **must** call that method upon completion of the
current request, whether the request was completed normally, or 
terminated early due to an error.  (This is to support resource release
by the application.  This protocol is intended to complement PEP 325's
generator support, and other common iterables with ``close()`` methods.

(Note: the application **must** invoke the ``start_response()`` 
callable before the iterable yields its first body string, so that the
server can send the headers before any body content.  However, this
invocation **may** be performed by the iterable's first iteration, so
servers **must not** assume that ``start_response()`` has been called
before they begin iterating over the iterable.)

Finally, servers and gateways **must not** directly use any other
attributes of the iterable returned by the application, unless it is an
instance of a type specific to that server or gateway, such as a "file
wrapper" returned by ``wsgi.file_wrapper`` (see `Optional 
Platform-Specific File Handling`_).  In the general case, only 
attributes specified here, or accessed via e.g. the PEP 234 iteration
APIs are acceptable.


``environ`` Variables
---------------------

The ``environ`` dictionary is required to contain these CGI
environment variables, as defined by the Common Gateway Interface
specification [2]_.  The following variables **must** be present,
unless their value would be an empty string, in which case they
**may** be omitted, except as otherwise noted below.

``REQUEST_METHOD``
  The HTTP request method, such as ``"GET"`` or ``"POST"``.  This 
  cannot ever be an empty string, and so is always required.

``SCRIPT_NAME`` 
  The initial portion of the request URL's "path" that corresponds to
  the application object, so that the application knows its virtual 
  "location".  This **may** be an empty string, if the application
  corresponds to the "root" of the server.  

``PATH_INFO``
  The remainder of the request URL's "path", designating the virtual 
  "location" of the request's target within the application.  This
  **may** be an empty string, if the request URL targets the 
  application root and does not have a trailing slash.

``QUERY_STRING``
  The portion of the request URL that follows the ``"?"``, if any.
  May be empty or absent.

``CONTENT_TYPE``
  The contents of any ``Content-Type`` fields in the HTTP request.
  May be empty or absent.

``CONTENT_LENGTH``
  The contents of any ``Content-Length`` fields in the HTTP request.
  May be empty or absent.

``SERVER_NAME``, ``SERVER_PORT``
  When combined with ``SCRIPT_NAME`` and ``PATH_INFO``, these variables
  can be used to complete the URL.  Note, however, that ``HTTP_HOST``,
  if present, should be used in   preference to ``SERVER_NAME`` for
  reconstructing the request URL.  See the `URL Reconstruction`_
  section below for more detail.   ``SERVER_NAME`` and ``SERVER_PORT``
  can never be empty strings, and so are always required.

``SERVER_PROTOCOL``
  The version of the protocol the client used to send the request.
  Typically this will be something like ``"HTTP/1.0"`` or ``"HTTP/1.1"``
  and may be used by the application to determine how to treat any
  HTTP request headers.  (This variable should probably be called
  ``REQUEST_PROTOCOL``, since it denotes the protocol used in the
  request, and is not necessarily the protocol that will be used in the
  server's response.  However, for compatibility with CGI we have to
  keep the existing name.)

``HTTP_`` Variables
  Variables corresponding to the client-supplied HTTP request headers
  (i.e., variables whose names begin with ``"HTTP_"``).  The presence or
  absence of these variables should correspond with the presence or
  absence of the appropriate HTTP header in the request.

A server or gateway **should** attempt to provide as many other CGI 
variables as are applicable.  In addition, if SSL is in use, the server
or gateway **should** also provide as many of the Apache SSL environment
variables [5]_ as are applicable, such as ``HTTPS=on`` and
``SSL_PROTOCOL``.  Note, however, that an application that uses any CGI
variables other than the ones listed above are necessarily non-portable
to web servers that do not support the relevant extensions.  (For
example, web servers that do not publish files will not be able to
provide a meaningful ``DOCUMENT_ROOT`` or ``PATH_TRANSLATED``.)

A WSGI-compliant server or gateway **should** document what variables
it provides, along with their definitions as appropriate.  Applications
**should** check for the presence of any variables they require, and 
have a fallback plan in the event such a variable is absent.

Note: missing variables (such as ``REMOTE_USER`` when no
authentication has occurred) should be left out of the ``environ``
dictionary.  Also note that CGI-defined variables must be strings,
if they are present at all.  It is a violation of this specification
for a CGI variable's value to be of any type other than ``str``.

In addition to the CGI-defined variables, the ``environ`` dictionary
**may** also contain arbitrary operating-system "environment variables",
and **must** contain the following WSGI-defined variables:

=====================  ===============================================
Variable               Value
=====================  ===============================================
``wsgi.version``       The tuple ``(1,0)``, representing WSGI
                       version 1.0.

``wsgi.url_scheme``    A string representing the "scheme" portion of
                       the URL at which the application is being 
                       invoked.  Normally, this will have the value
                       ``"http"`` or ``"https"``, as appropriate.

``wsgi.input``         An input stream (file-like object) from which
                       the HTTP request body can be read.  (The server
                       or gateway may perform reads on-demand as 
                       requested by the application, or it may pre-
                       read the client's request body and buffer it
                       in-memory or on disk, or use any other
                       technique for providing such an input stream,
                       according to its preference.)

``wsgi.errors``        An output stream (file-like object) to which 
                       error output can be written, for the purpose of
                       recording program or other errors in a
                       standardized and possibly centralized location.
                       This should be a "text mode" stream; i.e.,
                       applications should use ``"\n"`` as a line
                       ending, and assume that it will be converted to
                       the correct line ending by the server/gateway.

                       For many servers, ``wsgi.errors`` will be the
                       server's main error log. Alternatively, this
                       may be ``sys.stderr``, or a log file of some
                       sort.  The server's documentation should
                       include an explanation of how to configure this
                       or where to find the recorded output.  A server
                       or gateway may supply different error streams
                       to different applications, if this is desired.

``wsgi.multithread``   This value should evaluate true if the 
                       application object may be simultaneously
                       invoked by another thread in the same process,
                       and should evaluate false otherwise.

``wsgi.multiprocess``  This value should evaluate true if an 
                       equivalent application object may be 
                       simultaneously invoked by another process,
                       and should evaluate false otherwise.

``wsgi.run_once``      This value should evaluate true if the server
                       or gateway expects (but does not guarantee!)
                       that the application will only be invoked this
                       one time during the life of its containing
                       process.  Normally, this will only be true for
                       a gateway based on CGI (or something similar).
=====================  ===============================================

Finally, the ``environ`` dictionary may also contain server-defined
variables.  These variables should be named using only lower-case
letters, numbers, dots, and underscores, and should be prefixed with
a name that is unique to the defining server or gateway.  For
example, ``mod_python`` might define variables with names like
``mod_python.some_variable``.


Input and Error Streams
~~~~~~~~~~~~~~~~~~~~~~~

The input and error streams provided by the server must support
the following methods:

===================  ==========  ========
Method               Stream      Notes
===================  ==========  ========
``read(size)``       ``input``   1
``readline()``       ``input``   1,2
``readlines(hint)``  ``input``   1,3
``__iter__()``       ``input``
``flush()``          ``errors``  4
``write(str)``       ``errors``
``writelines(seq)``  ``errors``
===================  ==========  ========

The semantics of each method are as documented in the Python Library
Reference, except for these notes as listed in the table above:

1. The server is not required to read past the client's specified
   ``Content-Length``, and is allowed to simulate an end-of-file
   condition if the application attempts to read past that point.
   The application **should not** attempt to read more data than is
   specified by the ``CONTENT_LENGTH`` variable.

2. The optional "size" argument to ``readline()`` is not supported,
   as it may be complex for server authors to implement, and is not
   often used in practice.

3. Note that the ``hint`` argument to ``readlines()`` is optional for
   both caller and implementer.  The application is free not to
   supply it, and the server or gateway is free to ignore it.

4. Since the ``errors`` stream may not be rewound, servers and gateways
   are free to forward write operations immediately, without buffering.
   In this case, the ``flush()`` method may be a no-op.  Portable
   applications, however, cannot assume that output is unbuffered
   or that ``flush()`` is a no-op.  They must call ``flush()`` if
   they need to ensure that output has in fact been written.  (For
   example, to minimize intermingling of data from multiple processes
   writing to the same error log.)

The methods listed in the table above **must** be supported by all
servers conforming to this specification.  Applications conforming
to this specification **must not** use any other methods or attributes
of the ``input`` or ``errors`` objects.  In particular, applications
**must not** attempt to close these streams, even if they possess
``close()`` methods.


The ``start_response()`` Callable
---------------------------------

The second parameter passed to the application object is a callable
of the form ``start_response(status,response_headers,exc_info=None)``.
(As with all WSGI callables, the arguments must be supplied
positionally, not by keyword.)  The ``start_response`` callable is
used to begin the HTTP response, and it must return a
``write(body_data)`` callable (see the `Buffering and Streaming`_ 
section, below).

The ``status`` argument is an HTTP "status" string like ``"200 OK"``
or ``"404 Not Found"``.  That is, it is a string consisting of a 
Status-Code and a Reason-Phrase, in that order and separated by a 
single space, with no surrounding whitespace or other characters.
(See RFC 2616, Section 6.1.1 for more information.)  The string
**must not** contain control characters, and must not be terminated
with a carriage return, linefeed, or combination thereof.

The ``response_headers`` argument is a list of ``(header_name,
header_value)`` tuples.  It must be a Python list; i.e.
``type(response_headers) is ListType``, and the server **may** change
its contents in any way it desires.  Each ``header_name`` must be a
valid HTTP header field-name (as defined by RFC 2616, Section 4.2),
without a trailing colon or other punctuation.

Each ``header_value`` **must not** include *any* control characters,
including carriage returns or linefeeds, either embedded or at the end.
(These requirements are to minimize the complexity of any parsing that
must be performed by servers, gateways, and intermediate response
processors that need to inspect or modify response headers.)

In general, the server or gateway is responsible for ensuring that
correct headers are sent to the client: if the application omits
a header required by HTTP (or other relevant specifications that are in
effect), the server or gateway **must** add it.  For example, the HTTP
``Date:`` and ``Server:`` headers would normally be supplied by the
server or gateway.

(A reminder for server/gateway authors: HTTP header names are
case-insensitive, so be sure to take that into consideration when
examining application-supplied headers!)

Applications and middleware are forbidden from using HTTP/1.1
"hop-by-hop" features or headers, any equivalent features in HTTP/1.0,
or any headers that would affect the persistence of the client's 
connection to the web server.  These features are the
exclusive province of the actual web server, and a server or gateway
**should** consider it a fatal error for an application to attempt
sending them, and raise an error if they are supplied to 
``start_response()``.  (For more specifics on "hop-by-hop" features and
headers, please see the `Other HTTP Features`_ section below.)

The ``start_response`` callable **must not** actually transmit the
response headers.  Instead, it must store them for the server or
gateway to transmit **only** after the first iteration of the
application return value that yields a non-empty string, or upon
the application's first invocation of the ``write()`` callable.  In
other words, response headers must not be sent until there is actual
body data available, or until the application's returned iterable is
exhausted.  (The only possible exception to this rule is if the 
response headers explicitly include a ``Content-Length`` of zero.)

This delaying of response header transmission is to ensure that buffered
and asynchronous applications can replace their originally intended
output with error output, up until the last possible moment.  For
example, the application may need to change the response status from
"200 OK" to "500 Internal Error", if an error occurs while the body is
being generated within an application buffer.

The ``exc_info`` argument, if supplied, must be a Python
``sys.exc_info()`` tuple.  This argument should be supplied by the
application only if ``start_response`` is being called by an error
handler.  If ``exc_info`` is supplied, and no HTTP headers have been
output yet, ``start_response`` should replace the currently-stored
HTTP response headers with the newly-supplied ones, thus allowing the
application to "change its mind" about the output when an error has
occurred.

However, if ``exc_info`` is provided, and the HTTP headers have already
been sent, ``start_response`` **must** raise an error, and **should**
raise the ``exc_info`` tuple.  That is::

    raise exc_info[0],exc_info[1],exc_info[2]
    
This will re-raise the exception trapped by the application, and in
principle should abort the application.  (It is not safe for the 
application to attempt error output to the browser once the HTTP
headers have already been sent.)  The application **must not** trap
any exceptions raised by ``start_response``, if it called 
``start_response`` with ``exc_info``.  Instead, it should allow
such exceptions to propagate back to the server or gateway.  See
`Error Handling`_ below, for more details.

The application **may** call ``start_response`` more than once, if and
only if the ``exc_info`` argument is provided.  More precisely, it is
a fatal error to call ``start_response`` without the ``exc_info``
argument if ``start_response`` has already been called within the
current invocation of the application.  (See the example CGI
gateway above for an illustration of the correct logic.)

Note: servers, gateways, or middleware implementing ``start_response``
**should** ensure that no reference is held to the ``exc_info`` 
parameter beyond the duration of the function's execution, to avoid
creating a circular reference through the traceback and frames
involved.  The simplest way to do this is something like::

    def start_response(status,response_headers,exc_info=None):
        if exc_info:
             try:
                 # do stuff w/exc_info here
             finally:
                 exc_info = None    # Avoid circular ref.

The example CGI gateway provides another illustration of this
technique.


Handling the ``Content-Length`` Header
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the application does not supply a ``Content-Length`` header, a
server or gateway may choose one of several approaches to handling
it.  The simplest of these is to close the client connection when
the response is completed.

Under some circumstances, however, the server or gateway may be
able to either generate a ``Content-Length`` header, or at least
avoid the need to close the client connection.  If the application
does *not* call the ``write()`` callable, and returns an iterable
whose ``len()`` is 1, then the server can automatically determine
``Content-Length`` by taking the length of the first string yielded
by the iterable.

And, if the server and client both support HTTP/1.1 "chunked
encoding" [3]_, then the server **may** use chunked encoding to send
a chunk for each ``write()`` call or string yielded by the iterable,
thus generating a ``Content-Length`` header for each chunk.  This
allows the server to keep the client connection alive, if it wishes
to do so.  Note that the server **must** comply fully with RFC 2616
when doing this, or else fall back to one of the other strategies for
dealing with the absence of ``Content-Length``.

(Note: applications and middleware **must not** apply any kind of
``Transfer-Encoding`` to their output, such as chunking or gzipping;
as "hop-by-hop" operations, these encodings are the province of the 
actual web server/gateway.  See `Other HTTP Features`_ below, for
more details.)


Buffering and Streaming
-----------------------

Generally speaking, applications will achieve the best throughput
by buffering their (modestly-sized) output and sending it all at 
once.  This is a common approach in existing frameworks such as
Zope: the output is buffered in a StringIO or similar object, then
transmitted all at once, along with the response headers.

The corresponding approach in WSGI is for the application to simply
return a single-element iterable (such as a list) containing the
response body as a single string.  This is the recommended approach
for the vast majority of application functions, that render 
HTML pages whose text easily fits in memory.

For large files, however, or for specialized uses of HTTP streaming
(such as multipart "server push"), an application may need to provide
output in smaller blocks (e.g. to avoid loading a large file into 
memory).  It's also sometimes the case that part of a response may
be time-consuming to produce, but it would be useful to send ahead the
portion of the response that precedes it.

In these cases, applications will usually return an iterator (often
a generator-iterator) that produces the output in a block-by-block
fashion.  These blocks may be broken to coincide with mulitpart 
boundaries (for "server push"), or just before time-consuming 
tasks (such as reading another block of an on-disk file).

WSGI servers, gateways, and middleware **must not** delay the 
transmission of any block; they **must** either fully transmit
the block to the client, or guarantee that they will continue
transmission even while the application is producing its next block.
A server/gateway or middleware may provide this guarantee in one of
three ways:

1. Send the entire block to the operating system (and request 
   that any O/S buffers be flushed) before returning control
   to the application, OR
   
2. Use a different thread to ensure that the block continues
   to be transmitted while the application produces the next
   block.
   
3. (Middleware only) send the entire block to its parent
   gateway/server

By providing this guarantee, WSGI allows applications to ensure
that transmission will not become stalled at an arbitrary point
in their output data.  This is critical for proper functioning
of e.g. multipart "server push" streaming, where data between
multipart boundaries should be transmitted in full to the client.


Middleware Handling of Block Boundaries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to better support asynchronous applications and servers,
middleware components **must not** block iteration waiting for
multiple values from an application iterable.  If the middleware
needs to accumulate more data from the application before it can
produce any output, it **must** yield an empty string.

To put this requirement another way, a middleware component **must
yield at least one value** each time its underlying application 
yields a value.  If the middleware cannot yield any other value,
it must yield an empty string.

This requirement ensures that asynchronous applications and servers
can conspire to reduce the number of threads that are required
to run a given number of application instances simultaneously.

Note also that this requirement means that middleware **must**
return an iterable as soon as its underlying application returns
an iterable.  It is also forbidden for middleware to use the
``write()`` callable to transmit data that is yielded by an
underlying application.  Middleware may only use their parent
server's ``write()`` callable to transmit data that the 
underlying application sent using a middleware-provided ``write()``
callable.


The ``write()`` Callable
~~~~~~~~~~~~~~~~~~~~~~~~

Some existing application framework APIs support unbuffered
output in a different manner than WSGI.  Specifically, they
provide a "write" function or method of some kind to write
an unbuffered block of data, or else they provide a buffered
"write" function and a "flush" mechanism to flush the buffer.

Unfortunately, such APIs cannot be implemented in terms of
WSGI's "iterable" application return value, unless threads
or other special mechanisms are used.

Therefore, to allow these frameworks to continue using an
imperative API, WSGI includes a special ``write()`` callable,
returned by the ``start_response`` callable.

New WSGI applications and frameworks **should not** use the 
``write()`` callable if it is possible to avoid doing so.  The
``write()`` callable is strictly a hack to support imperative
streaming APIs.  In general, applications should produce their
output via their returned iterable, as this makes it possible
for web servers to interleave other tasks in the same Python thread,
potentially providing better throughput for the server as a whole.

The ``write()`` callable is returned by the ``start_response()``
callable, and it accepts a single parameter:  a string to be
written as part of the HTTP response body, that is treated exactly
as though it had been yielded by the output iterable.  In other
words, before ``write()`` returns, it must guarantee that the
passed-in string was either completely sent to the client, or
that it is buffered for transmission while the application
proceeds onward.

An application **must** return an iterable object, even if it
uses ``write()`` to produce all or part of its response body.
The returned iterable **may** be empty (i.e. yield no non-empty
strings), but if it *does* yield non-empty strings, that output 
must be treated normally by the server or gateway (i.e., it must be
sent or queued immediately).  Applications **must not** invoke
``write()`` from within their return iterable, and therefore any
strings yielded by the iterable are transmitted after all strings
passed to ``write()`` have been sent to the client.


Unicode Issues
--------------

HTTP does not directly support Unicode, and neither does this
interface.  All encoding/decoding must be handled by the application;
all strings passed to or from the server must be standard Python byte
strings, not Unicode objects.  The result of using a Unicode object 
where a string object is required, is undefined.

Note also that strings passed to ``start_response()`` as a status or
as response headers **must** follow RFC 2616 with respect to encoding.
That is, they must either be ISO-8859-1 characters, or use RFC 2047
MIME encoding.

On Python platforms where the ``str`` or ``StringType`` type is in
fact Unicode-based (e.g. Jython, IronPython, Python 3000, etc.), all
"strings" referred to in this specification must contain only 
code points representable in ISO-8859-1 encoding (``\u0000`` through
``\u00FF``, inclusive).  It is a fatal error for an application to 
supply strings containing any other Unicode character or code point.
Similarly, servers and gateways **must not** supply
strings to an application containing any other Unicode characters.

Again, all strings referred to in this specification **must** be
of type ``str`` or ``StringType``, and **must not** be of type
``unicode`` or ``UnicodeType``.  And, even if a given platform allows
for more than 8 bits per character in ``str``/``StringType`` objects,
only the lower 8 bits may be used, for any value referred to in
this specification as a "string".


Error Handling
--------------

In general, applications **should** try to trap their own, internal
errors, and display a helpful message in the browser.  (It is up
to the application to decide what "helpful" means in this context.)

However, to display such a message, the application must not have
actually sent any data to the browser yet, or else it risks corrupting
the response.  WSGI therefore provides a mechanism to either allow the
application to send its error message, or be automatically aborted:
the ``exc_info`` argument to ``start_response``.  Here is an example
of its use::

    try:
        # regular application code here
        status = "200 Froody"
        response_headers = [("content-type","text/plain")]
        start_response(status, response_headers)
        return ["normal body goes here"]  
    except:
        # XXX should trap runtime issues like MemoryError, KeyboardInterrupt
        #     in a separate handler before this bare 'except:'...
        status = "500 Oops"
        response_headers = [("content-type","text/plain")]
        start_response(status, response_headers, sys.exc_info())
        return ["error body goes here"]

If no output has been written when an exception occurs, the call to
``start_response`` will return normally, and the application will 
return an error body to be sent to the browser.  However, if any output
has already been sent to the browser, ``start_response`` will reraise 
the provided exception.  This exception **should not** be trapped by 
the application, and so the application will abort.  The server or
gateway can then trap this (fatal) exception and abort the response.

Servers **should** trap and log any exception that aborts an 
application or the iteration of its return value.  If a partial 
response has already been written to the browser when an application
error occurs, the server or gateway **may** attempt to add an error
message to the output, if the already-sent headers indicate a
``text/*`` content type that the server knows how to modify cleanly.

Some middleware may wish to provide additional exception handling 
services, or intercept and replace application error messages.  In
such cases, middleware may choose to **not** re-raise the ``exc_info``
supplied to ``start_response``, but instead raise a middleware-specific
exception, or simply return without an exception after storing the
supplied arguments.  This will then cause the application to return
its error body iterable (or invoke ``write()``), allowing the middleware
to capture and modify the error output.  These techniques will work as
long as application authors:

1. Always provide ``exc_info`` when beginning an error response

2. Never trap errors raised by ``start_response`` when ``exc_info`` is
   being provided


HTTP 1.1 Expect/Continue
------------------------

Servers and gateways that implement HTTP 1.1 **must** provide 
transparent support for HTTP 1.1's "expect/continue" mechanism.  This
may be done in any of several ways:

1. Respond to requests containing an ``Expect: 100-continue`` request
   with an immediate "100 Continue" response, and proceed normally.

2. Proceed with the request normally, but provide the application
   with a ``wsgi.input`` stream that will send the "100 Continue"
   response if/when the application first attempts to read from the
   input stream.  The read request must then remain blocked until the
   client responds.
   
3. Wait until the client decides that the server does not support
   expect/continue, and sends the request body on its own.  (This
   is suboptimal, and is not recommended.)

Note that these behavior restrictions do not apply for HTTP 1.0
requests, or for requests that are not directed to an application
object.  For more information on HTTP 1.1 Expect/Continue, see RFC
2616, sections 8.2.3 and 10.1.1.


Other HTTP Features
-------------------

In general, servers and gateways should "play dumb" and allow the
application complete control over its output.  They should only make
changes that do not alter the effective semantics of the application's
response.  It is always possible for the application developer to add
middleware components to supply additional features, so server/gateway
developers should be conservative in their implementation.  In a sense,
a server should consider itself to be like an HTTP "gateway server",
with the application being an HTTP "origin server".  (See RFC 2616,
section 1.3, for the definition of these terms.)

However, because WSGI servers and applications do not communicate via 
HTTP, what RFC 2616 calls "hop-by-hop" headers do not apply to WSGI
internal communications.  WSGI applications **must not** generate any
"hop-by-hop" headers [4]_, attempt to use HTTP features that would
require them to generate such headers, or rely on the content of
any incoming "hop-by-hop" headers in the ``environ`` dictionary.
WSGI servers **must** handle any supported inbound "hop-by-hop" headers
on their own, such as by decoding any inbound ``Transfer-Encoding``,
including chunked encoding if applicable.

Applying these principles to a variety of HTTP features, it should be 
clear that a server **may** handle cache validation via the
``If-None-Match`` and ``If-Modified-Since`` request headers and the
``Last-Modified`` and ``ETag`` response headers.  However, it is
not required to do this, and the application **should** perform its
own cache validation if it wants to support that feature, since
the server/gateway is not required to do such validation.

Similarly, a server **may** re-encode or transport-encode an
application's response, but the application **should** use a
suitable content encoding on its own, and **must not** apply a 
transport encoding.  A server **may** transmit byte ranges of the
application's response if requested by the client, and the 
application doesn't natively support byte ranges.  Again, however,
the application **should** perform this function on its own if desired.

Note that these restrictions on applications do not necessarily mean
that every application must reimplement every HTTP feature; many HTTP
features can be partially or fully implemented by middleware
components, thus freeing both server and application authors from
implementing the same features over and over again.
  

Thread Support
--------------

Thread support, or lack thereof, is also server-dependent.
Servers that can run multiple requests in parallel, **should** also
provide the option of running an application in a single-threaded
fashion, so that applications or frameworks that are not thread-safe
may still be used with that server.



Implementation/Application Notes
================================


Server Extension APIs
---------------------

Some server authors may wish to expose more advanced APIs, that
application or framework authors can use for specialized purposes.
For example, a gateway based on ``mod_python`` might wish to expose
part of the Apache API as a WSGI extension.

In the simplest case, this requires nothing more than defining an
``environ`` variable, such as ``mod_python.some_api``.  But, in many
cases, the possible presence of middleware can make this difficult.
For example, an API that offers access to the same HTTP headers that
are found in ``environ`` variables, might return different data if
``environ`` has been modified by middleware.

In general, any extension API that duplicates, supplants, or bypasses
some portion of WSGI functionality runs the risk of being incompatible
with middleware components.  Server/gateway developers should *not*
assume that nobody will use middleware, because some framework
developers specifically intend to organize or reorganize their
frameworks to function almost entirely as middleware of various kinds.

So, to provide maximum compatibility, servers and gateways that
provide extension APIs that replace some WSGI functionality, **must**
design those APIs so that they are invoked using the portion of the
API that they replace.  For example, an extension API to access HTTP
request headers must require the application to pass in its current
``environ``, so that the server/gateway may verify that HTTP headers
accessible via the API have not been altered by middleware.  If the
extension API cannot guarantee that it will always agree with
``environ`` about the contents of HTTP headers, it must refuse service
to the application, e.g. by raising an error, returning ``None``
instead of a header collection, or whatever is appropriate to the API.

Similarly, if an extension API provides an alternate means of writing
response data or headers, it should require the ``start_response``
callable to be passed in, before the application can obtain the
extended service.  If the object passed in is not the same one that
the server/gateway originally supplied to the application, it cannot
guarantee correct operation and must refuse to provide the extended
service to the application.

These guidelines also apply to middleware that adds information such
as parsed cookies, form variables, sessions, and the like to
``environ``.  Specifically, such middleware should provide these
features as functions which operate on ``environ``, rather than simply
stuffing values into ``environ``.  This helps ensure that information
is calculated from ``environ`` *after* any middleware has done any URL
rewrites or other ``environ`` modifications.

It is very important that these "safe extension" rules be followed by
both server/gateway and middleware developers, in order to avoid a
future in which middleware developers are forced to delete any and all
extension APIs from ``environ`` to ensure that their mediation isn't
being bypassed by applications using those extensions!


Application Configuration
-------------------------

This specification does not define how a server selects or obtains an
application to invoke.  These and other configuration options are
highly server-specific matters.  It is expected that server/gateway
authors will document how to configure the server to execute a
particular application object, and with what options (such as
threading options).

Framework authors, on the other hand, should document how to create an
application object that wraps their framework's functionality.  The
user, who has chosen both the server and the application framework,
must connect the two together.  However, since both the framework and
the server now have a common interface, this should be merely a
mechanical matter, rather than a significant engineering effort for
each new server/framework pair.

Finally, some applications, frameworks, and middleware may wish to
use the ``environ`` dictionary to receive simple string configuration
options.  Servers and gateways **should** support this by allowing
an application's deployer to specify name-value pairs to be placed in
``environ``.  In the simplest case, this support can consist merely of
copying all operating system-supplied environment variables from
``os.environ`` into the ``environ`` dictionary, since the deployer in
principle can configure these externally to the server, or in the
CGI case they may be able to be set via the server's configuration
files.

Applications **should** try to keep such required variables to a 
minimum, since not all servers will support easy configuration of 
them.  Of course, even in the worst case, persons deploying an 
application can create a script to supply the necessary configuration
values::

   from the_app import application
   
   def new_app(environ,start_response):
       environ['the_app.configval1'] = 'something'
       return application(environ,start_response)

But, most existing applications and frameworks will probably only need
a single configuration value from ``environ``, to indicate the location
of their application or framework-specific configuration file(s).  (Of
course, applications should cache such configuration, to avoid having
to re-read it upon each invocation.)


URL Reconstruction
------------------

If an application wishes to reconstruct a request's complete URL, it
may do so using the following algorithm, contributed by Ian Bicking::

    from urllib import quote
    url = environ['wsgi.url_scheme']+'://'

    if environ.get('HTTP_HOST'):
        url += environ['HTTP_HOST']
    else:
        url += environ['SERVER_NAME']

        if environ['wsgi.url_scheme'] == 'https':
            if environ['SERVER_PORT'] != '443':
               url += ':' + environ['SERVER_PORT']
        else:
            if environ['SERVER_PORT'] != '80':
               url += ':' + environ['SERVER_PORT']

    url += quote(environ.get('SCRIPT_NAME',''))
    url += quote(environ.get('PATH_INFO',''))
    if environ.get('QUERY_STRING'):
        url += '?' + environ['QUERY_STRING']

Note that such a reconstructed URL may not be precisely the same URI
as requested by the client.  Server rewrite rules, for example, may
have modified the client's originally requested URL to place it in a
canonical form.


Supporting Older (<2.2) Versions of Python
------------------------------------------

Some servers, gateways, or applications may wish to support older
(<2.2) versions of Python.  This is especially important if Jython
is a target platform, since as of this writing a production-ready
version of Jython 2.2 is not yet available.

For servers and gateways, this is relatively straightforward:
servers and gateways targeting pre-2.2 versions of Python must
simply restrict themselves to using only a standard "for" loop to
iterate over any iterable returned by an application.  This is the
only way to ensure source-level compatibility with both the pre-2.2
iterator protocol (discussed further below) and "today's" iterator
protocol (see PEP 234).

(Note that this technique necessarily applies only to servers,
gateways, or middleware that are written in Python.  Discussion of
how to use iterator protocol(s) correctly from other languages is
outside the scope of this PEP.)

For applications, supporting pre-2.2 versions of Python is slightly
more complex:

* You may not return a file object and expect it to work as an iterable,
  since before Python 2.2, files were not iterable.  (In general, you
  shouldn't do this anyway, because it will peform quite poorly most
  of the time!)  Use ``wsgi.file_wrapper`` or an application-specific
  file wrapper class.  (See `Optional Platform-Specific File Handling`_
  for more on ``wsgi.file_wrapper``, and an example class you can use
  to wrap a file as an iterable.)

* If you return a custom iterable, it **must** implement the pre-2.2
  iterator protocol.  That is, provide a ``__getitem__`` method that
  accepts an integer key, and raises ``IndexError`` when exhausted.
  (Note that built-in sequence types are also acceptable, since they
  also implement this protocol.)

Finally, middleware that wishes to support pre-2.2 versions of Python,
and iterates over application return values or itself returns an 
iterable (or both), must follow the appropriate recommendations above.

(Note: It should go without saying that to support pre-2.2 versions
of Python, any server, gateway, application, or middleware must also
use only language features available in the target version, use
1 and 0 instead of ``True`` and ``False``, etc.)


Optional Platform-Specific File Handling
----------------------------------------

Some operating environments provide special high-performance file-
transmission facilities, such as the Unix ``sendfile()`` call.
Servers and gateways **may** expose this functionality via an optional
``wsgi.file_wrapper`` key in the ``environ``.  An application
**may** use this "file wrapper" to convert a file or file-like object
into an iterable that it then returns, e.g.::

    if 'wsgi.file_wrapper' in environ:
        return environ['wsgi.file_wrapper'](filelike, block_size)
    else:
        return iter(lambda: filelike.read(block_size), '')

If the server or gateway supplies ``wsgi.file_wrapper``, it must be
a callable that accepts one required positional parameter, and one 
optional positional parameter.  The first parameter is the file-like
object to be sent, and the second parameter is an optional block
size "suggestion" (which the server/gateway need not use).  The
callable **must** return an iterable object, and **must not** perform
any data transmission until and unless the server/gateway actually
receives the iterable as a return value from the application.
(To do otherwise would prevent middleware from being able to interpret
or override the response data.)

To be considered "file-like", the object supplied by the application
must have a ``read()`` method that takes an optional size argument.
It **may** have a ``close()`` method, and if so, the iterable returned
by ``wsgi.file_wrapper`` **must** have a ``close()`` method that
invokes the original file-like object's ``close()`` method.  If the
"file-like" object has any other methods or attributes with names
matching those of Python built-in file objects (e.g. ``fileno()``),
the ``wsgi.file_wrapper`` **may** assume that these methods or
attributes have the same semantics as those of a built-in file object.

The actual implementation of any platform-specific file handling
must occur **after** the application returns, and the server or
gateway checks to see if a wrapper object was returned.  (Again,
because of the presence of middleware, error handlers, and the like,
it is not guaranteed that any wrapper created will actually be used.)
 
Apart from the handling of ``close()``, the semantics of returning a
file wrapper from the application should be the same as if the
application had returned ``iter(filelike.read, '')``.  In other words,
transmission should begin at the current position within the "file"
at the time that transmission begins, and continue until the end is
reached.

Of course, platform-specific file transmission APIs don't usually
accept arbitrary "file-like" objects.  Therefore, a
``wsgi.file_wrapper`` has to introspect the supplied object for
things such as a ``fileno()`` (Unix-like OSes) or a 
``java.nio.FileChannel`` (under Jython) in order to determine if
the file-like object is suitable for use with the platform-specific
API it supports.

Note that even if the object is *not* suitable for the platform API,
the ``wsgi.file_wrapper`` **must** still return an iterable that wraps
``read()`` and ``close()``, so that applications using file wrappers
are portable across platforms.  Here's a simple platform-agnostic
file wrapper class, suitable for old (pre 2.2) and new Pythons alike::

    class FileWrapper:

        def __init__(self, filelike, blksize=8192):
            self.filelike = filelike
            self.blksize = blksize
            if hasattr(filelike,'close'):
                self.close = filelike.close
                
        def __getitem__(self,key):
            data = self.filelike.read(self.blksize)
            if data:
                return data
            raise IndexError

and here is a snippet from a server/gateway that uses it to provide
access to a platform-specific API::

    environ['wsgi.file_wrapper'] = FileWrapper
    result = application(environ, start_response)
    
    try:
        if isinstance(result,FileWrapper):
            # check if result.filelike is usable w/platform-specific
            # API, and if so, use that API to transmit the result.
            # If not, fall through to normal iterable handling
            # loop below.

        for data in result:
            # etc.
            
    finally:
        if hasattr(result,'close'):
            result.close()    


Questions and Answers
=====================

1. Why must ``environ`` be a dictionary?  What's wrong with using a
   subclass?

   The rationale for requiring a dictionary is to maximize portability
   between servers.  The alternative would be to define some subset of
   a dictionary's methods as being the standard and portable
   interface.  In practice, however, most servers will probably find a
   dictionary adequate to their needs, and thus framework authors will
   come to expect the full set of dictionary features to be available,
   since they will be there more often than not.  But, if some server
   chooses *not* to use a dictionary, then there will be
   interoperability problems despite that server's "conformance" to
   spec.  Therefore, making a dictionary mandatory simplifies the
   specification and guarantees interoperabilty.

   Note that this does not prevent server or framework developers from
   offering specialized services as custom variables *inside* the
   ``environ`` dictionary.  This is the recommended approach for
   offering any such value-added services.

2. Why can you call ``write()`` *and* yield strings/return an
   iterable?  Shouldn't we pick just one way?

   If we supported only the iteration approach, then current
   frameworks that assume the availability of "push" suffer.  But, if
   we only support pushing via ``write()``, then server performance
   suffers for transmission of e.g. large files (if a worker thread
   can't begin work on a new request until all of the output has been
   sent).  Thus, this compromise allows an application framework to
   support both approaches, as appropriate, but with only a little
   more burden to the server implementor than a push-only approach
   would require.

3. What's the ``close()`` for?

   When writes are done during the execution of an application
   object, the application can ensure that resources are released
   using a try/finally block.  But, if the application returns an
   iterable, any resources used will not be released until the
   iterable is garbage collected.  The ``close()`` idiom allows an
   application to release critical resources at the end of a request,
   and it's forward-compatible with the support for try/finally in
   generators that's proposed by PEP 325.

4. Why is this interface so low-level?  I want feature X!  (e.g.
   cookies, sessions, persistence, ...)

   This isn't Yet Another Python Web Framework.  It's just a way for
   frameworks to talk to web servers, and vice versa.  If you want
   these features, you need to pick a web framework that provides the
   features you want.  And if that framework lets you create a WSGI
   application, you should be able to run it in most WSGI-supporting
   servers.  Also, some WSGI servers may offer additional services via
   objects provided in their ``environ`` dictionary; see the
   applicable server documentation for details.  (Of course,
   applications that use such extensions will not be portable to other
   WSGI-based servers.)

5. Why use CGI variables instead of good old HTTP headers?  And why
   mix them in with WSGI-defined variables?

   Many existing web frameworks are built heavily upon the CGI spec,
   and existing web servers know how to generate CGI variables.  In
   contrast, alternative ways of representing inbound HTTP information
   are fragmented and lack market share.  Thus, using the CGI
   "standard" seems like a good way to leverage existing
   implementations.  As for mixing them with WSGI variables,
   separating them would just require two dictionary arguments to be
   passed around, while providing no real benefits.

6. What about the status string?  Can't we just use the number,
   passing in ``200`` instead of ``"200 OK"``?

   Doing this would complicate the server or gateway, by requiring
   them to have a table of numeric statuses and corresponding
   messages.  By contrast, it is easy for an application or framework
   author to type the extra text to go with the specific response code
   they are using, and existing frameworks often already have a table
   containing the needed messages.  So, on balance it seems better to
   make the application/framework responsible, rather than the server
   or gateway.

7. Why is ``wsgi.run_once`` not guaranteed to run the app only once?

   Because it's merely a suggestion to the application that it should
   "rig for infrequent running".  This is intended for application
   frameworks that have multiple modes of operation for caching,
   sessions, and so forth.  In a "multiple run" mode, such frameworks
   may preload caches, and may not write e.g. logs or session data to
   disk after each request.  In "single run" mode, such frameworks
   avoid preloading and flush all necessary writes after each request.

   However, in order to test an application or framework to verify
   correct operation in the latter mode, it may be necessary (or at
   least expedient) to invoke it more than once.  Therefore, an
   application should not assume that it will definitely not be run
   again, just because it is called with ``wsgi.run_once`` set to
   ``True``.

8. Feature X (dictionaries, callables, etc.) are ugly for use in
   application code; why don't we use objects instead?

   All of these implementation choices of WSGI are specifically
   intended to *decouple* features from one another; recombining these
   features into encapsulated objects makes it somewhat harder to
   write servers or gateways, and an order of magnitude harder to
   write middleware that replaces or modifies only small portions of
   the overall functionality.

   In essence, middleware wants to have a "Chain of Responsibility"
   pattern, whereby it can act as a "handler" for some functions,
   while allowing others to remain unchanged.  This is difficult to do
   with ordinary Python objects, if the interface is to remain
   extensible.  For example, one must use ``__getattr__`` or
   ``__getattribute__`` overrides, to ensure that extensions (such as
   attributes defined by future WSGI versions) are passed through.

   This type of code is notoriously difficult to get 100% correct, and
   few people will want to write it themselves.  They will therefore
   copy other people's implementations, but fail to update them when
   the person they copied from corrects yet another corner case.

   Further, this necessary boilerplate would be pure excise, a
   developer tax paid by middleware developers to support a slightly
   prettier API for application framework developers.  But,
   application framework developers will typically only be updating
   *one* framework to support WSGI, and in a very limited part of
   their framework as a whole.  It will likely be their first (and
   maybe their only) WSGI implementation, and thus they will likely
   implement with this specification ready to hand.  Thus, the effort
   of making the API "prettier" with object attributes and suchlike
   would likely be wasted for this audience.

   We encourage those who want a prettier (or otherwise improved) WSGI
   interface for use in direct web application programming (as opposed
   to web framework development) to develop APIs or frameworks that
   wrap WSGI for convenient use by application developers.  In this
   way, WSGI can remain conveniently low-level for server and
   middleware authors, while not being "ugly" for application
   developers.


Proposed/Under Discussion
=========================

These items are currently being discussed on the Web-SIG and elsewhere,
or are on the PEP author's "to-do" list:

* Should ``wsgi.input`` be an iterator instead of a file?  This would
  help for asynchronous applications and chunked-encoding input
  streams.
  
* Optional extensions are being discussed for pausing iteration of an
  application's ouptut until input is available or until a callback
  occurs.
  
* Add a section about synchronous vs. asynchronous apps and servers,
  the relevant threading models, and issues/design goals in these
  areas.
  

Acknowledgements
================

Thanks go to the many folks on the Web-SIG mailing list whose
thoughtful feedback made this revised draft possible.  Especially:

* Gregory "Grisha" Trubetskoy, author of ``mod_python``, who beat up
  on the first draft as not offering any advantages over "plain old
  CGI", thus encouraging me to look for a better approach.

* Ian Bicking, who helped nag me into properly specifying the
  multithreading and multiprocess options, as well as badgering me to
  provide a mechanism for servers to supply custom extension data to
  an application.

* Tony Lownds, who came up with the concept of a ``start_response``
  function that took the status and headers, returning a ``write``
  function.  His input also guided the design of the exception handling
  facilities, especially in the area of allowing for middleware that
  overrides application error messages.
  
* Alan Kennedy, whose courageous attempts to implement WSGI-on-Jython
  (well before the spec was finalized) helped to shape the "supporting
  older versions of Python" section, as well as the optional
  ``wsgi.file_wrapper`` facility.

* Mark Nottingham, who reviewed the spec extensively for issues with
  HTTP RFC compliance, especially with regard to HTTP/1.1 features that
  I didn't even know existed until he pointed them out.
  

References
==========

.. [1] The Python Web Server Gateway Interface v1.0 - PEP 333
   (http://www.python.org/dev/peps/pep-0333/)

.. [2] The WSGI Wiki "Servers" topic
   (http://wsgi.org/wsgi/Servers)

.. [3] The WSGI Wiki "Frameworks" topic
   (http://wsgi.org/wsgi/Frameworks)

.. [4] Plack - Perl Web Server Gateway Interface
   (http://search.cpan.org/~miyagawa/PSGI-1.03/PSGI.pod)

.. [5] Rack - Ruby Web Server Gateway Interface
   (http://rack.rubyforge.org/doc/SPEC.html)

.. [6] Jack - JavaScript Web Server Gateway Interface
   (http://jackjs.org/jsgi-spec.html)



.. [1] The Python Wiki "Web Programming" topic
   (http://www.python.org/cgi-bin/moinmoin/WebProgramming)

.. [2] The Common Gateway Interface Specification, v 1.1, 3rd Draft
   (http://cgi-spec.golux.com/draft-coar-cgi-v11-03.txt)

.. [3] "Chunked Transfer Coding" -- HTTP/1.1, section 3.6.1
   (http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.6.1)

.. [4] "End-to-end and Hop-by-hop Headers" -- HTTP/1.1, Section 13.5.1 
   (http://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13.5.1)

.. [5] mod_ssl Reference, "Environment Variables"
   (http://www.modssl.org/docs/2.8/ssl_reference.html#ToC25)


Copyright
=========

This document has been placed in the public domain.



..
   Local Variables:
   mode: indented-text
   indent-tabs-mode: nil
   sentence-end-double-space: t
   fill-column: 70
   End:
