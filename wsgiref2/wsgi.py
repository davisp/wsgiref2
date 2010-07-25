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
        self.upgraded = False

        url_scheme = "http"
        script_name = ""

        for name, value in httpreq.headers:
            name = name.strip().lower()
            value = value.strip()
            if name == "host":
                parts = value.split(":", 1)
                server_address[0] = parts[0]
                if len(parts) > 1:
                    server_address[1] = int(parts[1])
            elif name == "x-forwarded-protocol" and value.lower() == "ssl":
                url_scheme = "https"
            elif name == "x-forwarded-ssl" and value.lower() == "on":
                url_scheme = "https"
            elif name == "x-script-name":
                script_name = value
            elif name == "expect" and value.lower() == "100-continue":
                httpreq.body.set_pre_read(self.pre_read)
            elif name == "transfer-encoding" and value.lower() == "chunked":
                self.body.set_trailer_handler(self.handle_trailers)

        self.environ = {
            "wsgi.version": (2, 0),
            "wsgi.uri_scheme": url_scheme,
            "wsgi.path": "",
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.upgrade": self.upgrade,
            "wsgi.upgraded": lambda: self.upgraded,
            "wsgi.errors": sys.stderr,

            "conn.server_name": server_address[0],
            "conn.server_port": server_address[1],
            "conn.remote_addr": client_address[0],
            "conn.remote_port": client_address[1],

            "http.method": httpreq.method
            "http.uri.raw": httpreq.uri,
            "http.uri.path": httpreq.path,
            "http.uri.query_string": httpreq.query_string
            "http.version": httpreq.version,
            "http.headers": {},
            "http.trailers": {},
            "http.body": httpreq.body
        }
        
        for (name, value) in httpreq.headers:
            name, value = name.strip.lower(), value.strip()
            self.environ["http.headers"].setdefault(name, []).append(value)

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

    def pre_read(self):
        self.socket.send("HTTP/1.1 100 Continue\r\n\r\n")

    def handle_trailers(self, trailers):
        for name, value in trailers:
            name, value = name.strip().lower(), value.strip()
            self.environ["http.trailers"].setdefault(name, []).append(value)

    def upgrade(self):
        if self.started:
            raise RuntimeError("Already upgraded.")
        self.started = True
        self.upgraded = True
        return self.socket

