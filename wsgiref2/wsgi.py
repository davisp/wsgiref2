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

        self.upgraded = False

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
                return
            (status, headers, body) = response
            resp = ["HTTP/%s.%s %s %s" % (self.httpreq.version[0],
                                        self.httpreq.version[1],
                                        status,
                                        util.STATUS_CODES[status])]
            for name, value in headers:
                resp.append("%s: %s" % (name, value))
            resp.extend(["", ""])
            resp = "\r\n".join(resp)
            self.socket.send(resp)
            for item in body:
                self.socket.send(item)
        except:
            tb = traceback.format_exc().encode("ascii", "replace")
            mesg = "HTTP/1.1 500 Internal Server Error\r\n\r\n%s" % tb
            self.socket.send(mesg)
            return False
        return True

    def upgrade(self):
        if self.upgraded:
            raise RuntimeError("Already upgraded.")
        self.upgraded = True
        return self.socket