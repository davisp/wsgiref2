# -*- coding: utf-8 -
#
# This file is part of wsgiref2 released under the MIT license. 
# See the NOTICE for more information.

import os
import re
import sys
import urlparse

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


class ParseError(Exception):
    """\
    A simple class for reporting errors that occur
    during parsing.
    """
    def __init__(self, error):
        self.error = error

    def __str__(self):
        return "<ParseError: %s>" % self.error


class Unreader(object):
    """\
    An Unreader is an object that can have previously read
    bytes pushed back into it to be re-read. This helps so
    that we don't have to read bytes one at a time.
    """
    def __init__(self, sock, max_chunk=8192):
        self.sock = sock
        self.max_chunk = max_chunk
        self.buf = StringIO()
    
    def _data(self):
        return self.sock.recv(self.max_chunk)
    
    def unread(self, data):
        self.buf.seek(0, os.SEEK_END)
        self.buf.write(data)
    
    def read(self, size=None):
        if size is not None and not isinstance(size, (int, long)):
            raise TypeError("size parameter must be an int or long.")
        if size == 0:
            return ""
        if size < 0:
            size = None

        self.buf.seek(0, os.SEEK_END)

        if size is None and self.buf.tell():
            ret = self.buf.getvalue()
            self.buf.truncate(0)
            return ret
        if size is None:
            return self._data()

        while self.buf.tell() < size:
            data = self._data()
            if not len(data):
                ret = self.buf.getvalue()
                self.buf.truncate(0)
                return ret
            self.buf.write(data)

        data = self.buf.getvalue()
        self.buf.truncate(0)
        self.buf.write(data[size:])
        return data[:size]


class LengthReader(object):
    """\
    A class that understands how to read up to a maximum
    number of bytes. Used for parsing request bodies that
    aren't passed using cunked encoding.
    """
    def __init__(self, unreader, length):
        self.unreader = unreader
        self.length = length
    
    def read(self, size):
        if not isinstance(size, (int, long)):
            raise TypeError("size must be an integral type")
        
        size = min(self.length, size)
        if size < 0:
            raise ValueError("Size must be positive.")
        if size == 0:
            return ""
        
        buf = StringIO()
        data = self.unreader.read()
        while data:
            buf.write(data)
            if buf.tell() >= size:
                break
            data = self.unreader.read()
        
        buf = buf.getvalue()
        ret, rest = buf[:size], buf[size:]
        self.unreader.unread(rest)
        self.length -= size
        return ret


class ChunkedReader(object):
    """\
    A class that is capable of decoding an HTTP request body
    that uses chunked transfer encoding. Also attempts to
    parse any trailers that may be present setting them on
    the request instance.
    """
    def __init__(self, unreader, req):
        self.parser = self.parse_chunked(unreader)
        self.req = req
        self.buf = StringIO()
    
    def read(self, size):
        if not isinstance(size, (int, long)):
            raise TypeError("size must be an integral type")
        if size <= 0:
            raise ValueError("Size must be positive.")
        if size == 0:
            return ""

        if self.parser:
            while self.buf.tell() < size:
                try:
                    self.buf.write(self.parser.next())
                except StopIteration:
                    self.parser = None
                    break

        data = self.buf.getvalue()
        ret, rest = data[:size], data[size:]
        self.buf.truncate(0)
        self.buf.write(rest)
        return ret
    
    def parse_trailers(self, unreader, data):
        buf = StringIO()
        buf.write(data)
        
        idx = buf.getvalue().find("\r\n\r\n")
        done = buf.getvalue()[:2] == "\r\n"
        while idx < 0 and not done:
            self.get_data(unreader, buf)
            idx = buf.getvalue().find("\r\n\r\n")
            done = buf.getvalue()[:2] == "\r\n"
        if done:
            unreader.unread(buf.getvalue()[2:])
            return ""
        self.req.trailers = self.req.parse_headers(buf.getvalue()[:idx])
        unreader.unread(buf.getvalue()[idx+4:])

    def parse_chunked(self, unreader):
        (size, rest) = self.parse_chunk_size(unreader)
        while size > 0:
            while size > len(rest):
                size -= len(rest)
                yield rest
                rest = unreader.read()
                if not rest:
                    raise ParseError("Client disconected during chunk.")
            yield rest[:size]
            # Remove \r\n after chunk
            rest = rest[size:]
            while len(rest) < 2:
                rest += unreader.read()
            if rest[:2] != '\r\n':
                raise ParseError("Chunk is missing the \\r\\n terminator.")
            (size, rest) = self.parse_chunk_size(unreader, data=rest[2:])          

    def parse_chunk_size(self, unreader, data=None):
        buf = StringIO()
        if data is not None:
            buf.write(data)

        idx = buf.getvalue().find("\r\n")
        while idx < 0:
            self.get_data(unreader, buf)
            idx = buf.getvalue().find("\r\n")

        data = buf.getvalue()
        line, rest_chunk = data[:idx], data[idx+2:]
    
        chunk_size = line.split(";", 1)[0].strip()
        try:
            chunk_size = int(chunk_size, 16)
        except ValueError:
            raise ParseError("Invalid chunk size: %r" % chunk_size)

        if chunk_size == 0:
            try:
                self.parse_trailers(unreader, rest_chunk)
            except NoMoreData:
                pass
            return (0, None)
        return (chunk_size, rest_chunk)

    def get_data(self, unreader, buf):
        data = unreader.read()
        if not data:
            raise ParseError("Client disconnected while reading chunked body.")
            raise NoMoreData()
        buf.write(data)


class Body(object):
    """\
    This class implements the necessary methods specified by
    WSGI v1.0.
    """
    def __init__(self, reader):
        self.reader = reader
        self.buf = StringIO()
    
    def __iter__(self):
        return self
    
    def next(self):
        ret = self.readline()
        if not ret:
            raise StopIteration()
        return ret

    def discard(self):
        """\
        If processing a request failed to read all the available
        body data we need to discard anything before processing
        the nest request.
        """
        data = self.read(8192)
        while data:
            data = self.read(8192)
    
    def read(self, size=None):
        size = self._get_size(size)
        if size == 0:
            return ""

        if size < self.buf.tell():
            data = self.buf.getvalue()
            ret, rest = data[:size], data[size:]
            self.buf.truncate(0)
            self.buf.write(rest)
            return ret

        while size > self.buf.tell():
            data = self.reader.read(1024)
            if not len(data):
                break
            self.buf.write(data)

        data = self.buf.getvalue()
        ret, rest = data[:size], data[size:]
        self.buf.truncate(0)
        self.buf.write(rest)
        return ret
    
    def readline(self, size=None):
        size = self._get_size(size)
        if size == 0:
            return ""
        
        idx = self.buf.getvalue().find("\n")
        while idx < 0:
            data = self.reader.read(1024)
            if not len(data):
                break
            self.buf.write(data)
            idx = self.buf.getvalue().find("\n")
            if size < self.buf.tell():
                break
        
        # If we didn't find it, and we got here, we've
        # exceeded size or run out of data.
        if idx < 0:
            rlen = min(size, self.buf.tell())
        else:
            rlen = idx + 1

            # If rlen is beyond our size threshold, trim back
            if rlen > size:
                rlen = size
        
        data = self.buf.getvalue()
        ret, rest = data[:rlen], data[rlen:]
        
        self.buf.truncate(0)
        self.buf.write(rest)
        return ret
    
    def readlines(self, size=None):
        ret = []
        data = self.read()
        while len(data):
            pos = data.find("\n")
            if pos < 0:
                ret.append(data)
                data = ""
            else:
                line, data = data[:pos+1], data[pos+1:]
                ret.append(line)
        return ret

    def _get_size(self, size):
        """\
        Correct a size hint passed in to a read request. This
        attempts to mimic the behaviour of a file object.
        """
        if size is None:
            return sys.maxint
        elif not isinstance(size, (int, long)):
            raise TypeError("Size must be an integral type")
        elif size < 0:
            return sys.maxint
        return size

class Request(object):
    def __init__(self, unreader):
        self.unreader = unreader

        self.methre = re.compile("[A-Z0-9$-_.]{3,20}")
        self.versre = re.compile("HTTP/(\d+).(\d+)")
        self.hdrre = re.compile("[\x00-\x1F\x7F()<>@,;:\[\]={} \t\\\\\"]")

        self.method = None
        self.uri = None
        self.scheme = None
        self.host = None
        self.port = 80
        self.path = None
        self.query = None
        self.fragment = None
        self.version = None
        self.headers = []
        self.trailers = []
        self.body = None

        unused = self.parse(self.unreader)
        self.unreader.unread(unused)
        self.set_body_reader()
    
    def parse(self, unreader):
        buf = StringIO()

        self._get_data(unreader, buf, stop=True)
        
        # Request line
        idx = buf.getvalue().find("\r\n")
        while idx < 0:
            self._get_data(unreader, buf)
            idx = buf.getvalue().find("\r\n")
        self.parse_request_line(buf.getvalue()[:idx])
        rest = buf.getvalue()[idx+2:] # Skip \r\n
        buf.truncate(0)
        buf.write(rest)
        
        # Headers
        idx = buf.getvalue().find("\r\n\r\n")
        done = buf.getvalue()[:2] == "\r\n"
        while idx < 0 and not done:
            self._get_data(unreader, buf)
            idx = buf.getvalue().find("\r\n\r\n")
            done = buf.getvalue()[:2] == "\r\n"
        if done:
            self.unreader.unread(buf.getvalue()[2:])
            return ""
        self.headers = self.parse_headers(buf.getvalue()[:idx])

        ret = buf.getvalue()[idx+4:]
        buf.truncate(0)
        return ret

    def parse_request_line(self, line):
        bits = line.split(None, 2)
        if len(bits) != 3:
            raise ParseError("Invalid request line. %r" % line.strip())

        # Method
        if not self.methre.match(bits[0]):
            raise ParseError("Invalid request line. Bad method: %r" % bits[0])
        self.method = bits[0].upper()

        # URI
        self.uri = bits[1]
        parts = urlparse.urlparse(bits[1])
        self.scheme = parts.scheme or ''
        self.host = parts.netloc or None
        if parts.port is None:
            self.port = 80
        else:
            self.host = self.host.rsplit(":", 1)[0]
            self.port = parts.port
        self.path = parts.path or ""
        self.query = parts.query or ""
        self.fragment = parts.fragment or ""

        # Version
        match = self.versre.match(bits[2])
        if match is None:
            raise ParseError("Invalid HTTP version: %r" % bits[2])
        self.version = (int(match.group(1)), int(match.group(2)))

    def parse_headers(self, data):
        headers = []

        # Split lines on \r\n keeping the \r\n on each line
        lines = []
        while len(data):
            pos = data.find("\r\n")
            if pos < 0:
                lines.append(data)
                data = ""
            else:
                lines.append(data[:pos+2])
                data = data[pos+2:]

        # Parse headers into key/value pairs paying attention
        # to continuation lines.
        while len(lines):
            # Parse initial header name : value pair.
            curr = lines.pop(0)
            if curr.find(":") < 0:
                raise ParseError("Invalid header. No colon separator found.")
            name, value = curr.split(":", 1)
            name = name.rstrip(" \t").upper()
            if self.hdrre.search(name):
                raise ParseError("Invalid header. Invalid bytes: %r" % name)
            name, value = name.strip(), [value.lstrip()]
            
            # Consume value continuation lines
            while len(lines) and lines[0].startswith((" ", "\t")):
                value.append(lines.pop(0))
            value = ''.join(value).rstrip()
            
            headers.append((name, value))
        return headers

    def set_body_reader(self):
        chunked = False
        clength = 0

        for (name, value) in self.headers:
            if name.lower() == "content-length":
                try:
                    clength = int(value)
                except ValueError:
                    clength = 0
            elif name.lower() == "transfer-encoding":
                chunked = value.lower() == "chunked"
            elif name.lower() == "sec-websocket-key1":
                clength = 8

        if chunked:
            self.body = Body(ChunkedReader(self.unreader, self))
        else:
            self.body = Body(LengthReader(self.unreader, clength))

    def should_close(self):
        for (h, v) in self.headers:
            if h.lower() == "connection":
                if v.lower().strip() == "close":
                    return True
                elif v.lower().strip() == "keep-alive":
                    return False
        return self.version <= (1, 0)

    def _get_data(self, unreader, buf, stop=False):
        data = unreader.read()
        if not data:
            if stop:
                raise StopIteration()
            raise ParseError("Client closed prematurely.")
        buf.write(data)



