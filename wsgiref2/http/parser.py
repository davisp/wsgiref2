# -*- coding: utf-8 -
#
# This file is part of wsgiref2 released under the MIT license. 
# See the NOTICE for more information.

__all__ = ["RequestParser"]

from request import Request
from unreader import SocketUnreader, IterUnreader

class RequestParser(object):
    def __init__(self, source):
        if hasattr(source, "recv"):
            self.unreader = SocketUnreader(source)
        else:
            self.unreader = IterUnreader(source)
        self.request = None

    def __iter__(self):
        return self
    
    def next(self):
        # Stop if HTTP dictates a stop.
        if self.request and self.request.should_close():
            raise StopIteration()
        
        # Discard any unread body of the previous message
        if self.request:
            data = self.request.body.read(8192)
            while data:
                data = self.request.body.read(8192)
        
        # Parse the next request
        self.request = Request(self.unreader)
        if not self.request:
            raise StopIteration()
        return self.request
