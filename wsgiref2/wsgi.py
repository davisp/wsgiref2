# -*- coding: utf-8 -
#
# This file is part of wsgiref2 released under the MIT license. 
# See the NOTICE for more information.

import sys

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
        
        for val in self.environ["http.header.trailers"]:
            if val.strip():
                self.environ["http.has_trailers"] = True

    def upgrade(self):
        if self.upgraded:
            raise RuntimeError("Already upgraded.")
        self.upgraded = True
        return self.socket