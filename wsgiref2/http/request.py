# -*- coding: utf-8 -
#
# This file is part of wsgiref2 released under the MIT license. 
# See the NOTICE for more information.

__all__ = ["Request"]

import re
import urlparse

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from body import Body, ChunkedReader, LengthReader
from errors import *

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
            raise InvalidRequestLine(line)

        # Method
        if not self.methre.match(bits[0]):
            raise InvalidRequestMethod(bits[0])
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
            raise InvalidHTTPVersion(bits[2])
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
                raise InvalidHeader(curr.strip())
            name, value = curr.split(":", 1)
            name = name.rstrip(" \t").upper()
            if self.hdrre.search(name):
                raise InvalidHeaderName(name)
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
            if name.upper() == "CONTENT-LENGTH":
                try:
                    clength = int(value)
                except ValueError:
                    clength = 0
            elif name.upper() == "TRANSFER-ENCODING":
                chunked = value.lower() == "chunked"
            elif name.upper() == "SEC-WEBSOCKET-KEY1":
                clength = 8

        if chunked:
            self.body = Body(ChunkedReader(self, self.unreader))
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
            raise NoMoreData(buf.getvalue())
        buf.write(data)

