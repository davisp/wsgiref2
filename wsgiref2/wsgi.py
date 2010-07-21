# -*- coding: utf-8 -
#
# This file is part of wsgiref2 released under the MIT license. 
# See the NOTICE for more information.

import sys
import traceback

import wsgiref2.util as util

class Request(object):
    def __init__(self, server_address, client_address, socket, httpreq):
        self.server_address = server_address
        self.client_address = client_address
        self.socket = socket
        self.httpreq = httpreq
        self.started = False

        self.environ = {
            "http.method": httpreq.method,
            "http.uri": httpreq.uri,
            "http.scheme": httpreq.scheme,
            "http.host": httpreq.host,
            "http.port": httpreq.port,
            "http.path": httpreq.path,
            "http.query_string": httpreq.query,
            "http.fragment": httpreq.fragment,
            "http.version": httpreq.version,
            "http.has_trailers": False,
            "http.body": httpreq.body,
            "wsgi.errors": sys.stderr,
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.upgrade": self.upgrade
        }
        
        for (header, value) in httpreq.headers:
            name = "http.header.%s" % header.lower()
            self.environ.setdefault(name, []).append(value)
        
        for val in self.environ.get("http.header.trailers", []):
            if val.strip():
                self.environ["http.has_trailers"] = True

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
                ("Content-Type", "text/plain"),
                ("Content-Length", str(len(tb)))
            ]
            self.respond(500, headers, [tb])
        return True

    def respond(self, status, headers, body):
        front = ["HTTP/1.1 %d %s" % (status, util.STATUS_CODES[status])]
        for name, value in headers:
            front.append("%s: %s" % (name, value))
        front.extend(["", ""])
        self.started = True
        self.socket.send("\r\n".join(front))
        for data in body:
            self.socket.send(data)

    def upgrade(self):
        if self.started:
            raise RuntimeError("Already upgraded.")
        self.started = True
        return self.socket

