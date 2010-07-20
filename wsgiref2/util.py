# -*- coding: utf-8 -
#
# This file is part of wsgiref2 released under the MIT license. 
# See the NOTICE for more information.

def parse_addr(spec):
    try:
        ip, port = spec.split(":", 1)
        port = int(port)
        return ip, port
    except:
        pass

    try:
        port = int(spec)
        return "127.0.0.1", port
    except:
        pass

    try:
        parts = spec.split(".", 3)
        for p in parts:
            p = int(p)
            assert 0 <= p <= 255
        return spec, 8000
    except:
        pass