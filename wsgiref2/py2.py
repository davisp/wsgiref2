
try:
    from cStringIO import StringIO as BufferIO
except ImportError:
    from StringIO import StringIO as BufferIO

def b(value):
    return value