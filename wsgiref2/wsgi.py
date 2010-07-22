# -*- coding: utf-8 -
#
# This file is part of wsgiref2 released under the MIT license. 
# See the NOTICE for more information.

import sys
import traceback

from wsgiref2.util import b, STATUS_CODES

class Request(object):
    def __init__(self, server_address, client_address, socket, httpreq):
        self.server_address = server_address
        self.client_address = client_address
        self.socket = socket
        self.httpreq = httpreq
        self.started = False

        self.environ = {
            b("http.method"): httpreq.method,
            b("http.uri.raw"): httpreq.uri,
            b("http.uri.scheme"): httpreq.scheme,
            b("http.uri.userinfo"): httpreq.userinfo,
            b("http.uri.host"): httpreq.host,
            b("http.uri.port"): httpreq.port,
            b("http.uri.path"): httpreq.path,
            b("http.uri.query_string"): httpreq.query,
            b("http.uri.fragment"): httpreq.fragment,
            b("http.version"): httpreq.version,
            b("http.has_trailers"): False,
            b("http.body"): httpreq.body,
            b("wsgi.errors"): sys.stderr,
            b("wsgi.multithread"): False,
            b("wsgi.multiprocess"): False,
            b("wsgi.upgrade"): self.upgrade
        }
        
        for (header, value) in httpreq.headers:
            name = b("http.header.") + header.lower()
            self.environ.setdefault(name, []).append(value)
        
        for val in self.environ.get(b("http.header.trailers"), []):
            if val.strip():
                self.environ[b("http.has_trailers")] = True

    def handle(self, app):
        try:
            response = app(self.environ)
            if response is None:
                return False
            (status, headers, body) = response
            self.respond(status, headers, body)
        except:
            if self.started:
                raise
            tb = traceback.format_exc().encode("ascii", "replace")
            headers = [
                (b("Content-Type"), b("text/plain")),
                (b("Content-Length"), b(str(len(tb))))
            ]
            self.respond(500, headers, [tb])
        return True

    def respond(self, status, headers, body):
        front = [b("HTTP/1.1 %d %s" % (status, STATUS_CODES[status]))]
        for name, value in headers:
            front.append(name + b(": ") + value)
        front.extend([b(""), b("")])
        self.started = True
        self.socket.send(b("\r\n").join(front))
        for data in body:
            self.socket.send(data)

    def upgrade(self):
        if self.started:
            raise RuntimeError("Already upgraded.")
        self.started = True
        return self.socket

