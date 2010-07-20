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
        self.server_address = address
        self.backlog = 64

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(address)
        self.sock.listen(self.backlog)
        
        self.app = None
    
    def run(self):
        while True:
            sock, addr = self.sock.accept()
            try:
                parser = http.RequestParser(sock)
                for req in parser:
                    self.handle(sock, addr, req)
            except:
                traceback.print_exc()
            finally:
                sock.close()

    def handle(self, sock, addr, httpreq):
        try:
            wsgireq = wsgi.Request(self.server_address, addr, sock, httpreq)
            response = self.app(wsgireq.environ)
            if response is None:
                return
            (status, headers, body) = response
            resp = ["HTTP/%s.%s %s"] % (httpreq.version[0],
                                        httpreq.version[1], status)
            for name, value in headers:
                resp.append("%s: %s" % name, value)
            resp.append("")
            resp = "\r\n".join(resp)
            sock.write(resp)
            for item in resp:
                sock.write(item)
        except:
            tb = traceback.format_exc().encode("ascii", "replace")
            mesg = "HTTP/1.1 500 Internal Server Error\r\n\r\n%s" % tb
            sock.write(mesg)

def main():
    parser = op.OptionParser(usage=__usage__, option_list=options())
    opts, args = parser.parse_args()

    if len(args) > 0:
        parser.error("Unrecognized arguments: %s" % ", ".join(args))

    address = util.parse_addr(opts.bind)
    if not address:
        parser.error("Invalid bind value: %s" % opts.bind)    

    server = HTTPServer(address)

    try:
        server.run()
    except KeyboardInterrupt():
        pass
    
def options():
    return [
        op.make_option("-b", "--bind", dest="bind", metavar="IP:PORT",
            default="127.0.0.1:8000",
            help="Both IP and PORT are optional. [%default]"),
    ]


