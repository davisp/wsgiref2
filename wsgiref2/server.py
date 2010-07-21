# -*- coding: utf-8 -
#
# This file is part of wsgiref2 released under the MIT license. 
# See the NOTICE for more information.

import optparse as op
import socket
import traceback

import wsgiref2.http as http
import wsgiref2.util as util
import wsgiref2.wsgi as wsgi

__usage__ = "usage: %prog [OPTIONS]"

class HTTPServer(object):
    def __init__(self, address):
        self.address = address
        self.backlog = 64

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(address)
        self.sock.listen(self.backlog)
        
    def app(self, environ):
        status = 200
        body = "Hello, World!\n"
        headers = [
            ("Content-Type", "text/plain"),
            ("Content-Length", str(len(body)))
        ]
        return status, headers, body
    
    def run(self):
        while True:
            sock, addr = self.sock.accept()
            try:
                for req in self.requests(sock, addr):
                    if not req.handle(self.app):
                        break
            except KeyboardInterrupt:
                raise
            except:
                traceback.print_exc()
            finally:
                sock.close()

    def requests(self, socket, address):
        unreader = http.Unreader(socket)
        while True:
            httpreq = http.Request(unreader)
            wsgireq = wsgi.Request(self.address, address, socket, httpreq)
            yield wsgireq
            if httpreq.should_close():
                break        

def main():
    parser = op.OptionParser(usage=__usage__, option_list=options())
    opts, args = parser.parse_args()

    if len(args) > 0:
        parser.error("Unrecognized arguments: %s" % ", ".join(args))

    address = (opts.ip, opts.port)
    
    try:
        HTTPServer(address).run()
    except KeyboardInterrupt:
        pass
    
def options():
    return [
        op.make_option("-i", "--ip", dest="ip", default="127.0.0.1",
            help="The ip address to bind to. [%default]"),
        op.make_option("-p", "--port", dest="port", type="int", default=8000,
            help="The port to serve from. [%default]"),
    ]

if __name__ == '__main__':
    main()
