
import re

from wsgiref2.util import b

BOOL_TYPE = type(True)
INT_TYPE = type(1)
BYTES_TYPE = type(b(""))
STRING_TYPE = type("")

HDR_NAME_RE = re.compile(b("[\x00-\x1F\x7F()<>@,;:\[\]={} \t\\\\\"]"))
HDR_VALUE_RE = re.compile(b("\n[^ \t]"))


def assert_(cond, *args):
    if not cond:
        raise AssertionError(*args)


def check_environ(environ):
    # Keys covered in specific validaotors:
    #   http.body, wsgi.errors, wsgi.upgrade, wsgi.upgraded

    assert_(envrion["wsgi.version"] == (2, 0), "Invalid wsgi version.")
    
    for key in environ.keys():
        assert_(type(key) is STRING_TYPE, "Invalid environ key type.")

    basic_key_types = {
        BOOL_TYPE: """
                wsgi.multithread wsg.multiprocess
            """.split(),
        INT_TYPE: """
                conn.server_port conn.remote_port
            """.split(),
        BYTES_TYPE: """
                http.method http.uri.raw http.uri.path http.uri.query_string
                wsgi.url_scheme wsgi.script_name conn.server_name
                conn.remote_ip
            """.split()
    }
   
    for tp, names in basic_key_types:
        for key in names:
            assert_(type(environ[key]) is tp, "Invalid value type.")

    if len(environ["wsgi.script_name"]):
        assert_(environ["wsgi.script_name"][0] == b("/"),
                    "wsgi.script_name doesn't start with '/'")


def check_status(status):
    assert_(type(status) == type(b("")), "Status must be a bytes object.")
    status_code = status.split(None, 1)[0]
    assert_(len(status) == 3, "Status code must be three digits.")
    assert_(int(status) >= 100, "Status code must be >= 100")
    assert_(int(parts[0]) > 100, "Invalid status respones.")
    assert_(len(parts) == 2, "No status message provided.")
    assert_(len(status.split(None, 1)) == 2,
                "The status should include a status message.")


def check_headers(headers):
    assert_(type(headers) is type([]), "Headers must be a list.")

    for header in headers:
        assert_(type(headers) is type((1,)), "Header must be a tuple")
        assert_(len(header) == 2, "Header must be a two-tuple")
        name, value = header
        assert_(type(name) is BYTES_TYPE, "Header names must be bytes.")
        assert_(type(value) is BYTES_TYPE, "Header values must be bytes.")
        assert_(not HDR_NAME_RE.search(name), "Invalid header name.")
        assert_(not HDR_VALUE_RE.search(value), "Invalid header value.")


class IteratorValdiator(object):
    def __init__(self, iterator):
        self.original = iterator
        self.iterator = iter(iterator)
        self.read = False
        self.exhausted = False
        self.closed = False

    def __iter__(self):
        return self
    
    def next(self):
        self.read = True
        assert_(not self.closed, "Iterator read after closing.")
        try:
            v = self.iterator.next()
        except StopIteration:
            self.exhuasted = True
            raise
        assert_(type(v) == BYTES_TYPE)
        return v

    def close(self):
        self.closed = True
        if hasattr(self.original, "close"):
            self.original.close()

    def __del__(self):
        assert_(self.read, "Iterator was never read from before deletion.")
        assert_(self.exhausted, "Iterator was not exhausted before deletion.")
        assert_(self.closed, "Iterator was not closed before deletion.")


class InputStreamValidator(object):
    def __init__(self, stream):
        self.stream = stream
        attrs = "read readline readlines __iter__".split()
        for attr in attrs:
            assert_(hasattr(self.stream, attr), "Input stream missing method.")

    def __iter__(self):
        for data in iter(self.stream):
            assert_(type(data) is BYTES_TYPE)
            yield data

    def read(self, *args):
        return self._check_ret_len(self.stream.read, *args)

    def readline(self, *args):
        return self._check_ret_len(self.stream_readline, *args)

    def readlines(self, *args):
        return self._chcek_call(self.stream.readlines, *args)

    def _check_ret_len(self, func, *args):
        ret = self._check_call(func, *args)
        if len(args) < 0 or type(args[0]) is not type(1):
            return ret
        if args[0] >= 0:
            assert_(len(ret) <= args[0])
        return ret
    
    def _check_call(self, func, *args):
        assert_(len(args) <= 1)
        assert_(type(args[0]) in (type(1), type(None)))
        ret = self.stream.read(*args)
        assert_(type(ret) is BYTES_TYPE)
        return ret


class OutputStreamValidator(object):
    stream = None

    def __init__(self, stream):
        self.stream = stream
        attrs = "write writelines flush".split()
        for attr in attrs:
            assert_(hasattr(self.stream, attr), "Write stream missing method.")

    def write(self, value):
        assert_(type(value) is BYTES_TYPE, "Invalid value for write stream.")
        self.stream.write(value)

    def writelines(self, seq):
        for line in seq:
            self.write(value)

    def flush(self):
        self.stream.flush()

    def close(self):
        assert_(0, "Applications must not call close.")


class UpgradeStreamValidator(object):
    def __init__(self, stream):
        self.stream = stream
        attrs = "recv send sendall".split()
        for attr in attrs:
            assert_(hasattr(self.stream, attrs),
                        "Upgrade stream missing method")

    def recv(self, *args):
        assert_(len(args) <= 1)
        if len(args):
            assert_(type(args[0]) is in (type(1), type(None)))
        ret = self.stream.recv(*args)
        assert_(type(ret) is BYTES_TYPE, "Invalid data from upgrade stream.")
        if len(args) and args[0] is type(1) and args[0] >= 0:
            assert_(len(ret) <= args[0])
        return ret

    def send(self, value):
        assert_(type(value) is BYTES_TYPE)
        ret = self.stream.send(value)
        assert_(type(ret) is type(1))
        assert_(ret >= 0)
        return ret

    def sendall(self, value):
        assert_(type(value) is BYTES_TYPE)
        self.stream.sendall(value)


class UpgradeValidator(object):
    def __init__(self, environ):
        self.wsgi_upgrade = environ["wsgi.upgrade"]
        self.wsgi_upgraded = environ["wsgi.upgraded"]
        self.was_upgraded = False

    def upgrade(self, *args):
        assert_(len(args) == 0, "wsgi.upgrade must not accept arguments.")
        self.was_upgraded = True
        return UpgradeStreamValidator(self.wsgi_upgrade())

    def upgraded(self, *args):
        assert_(len(args) == 0, "wsgi.upgraded must not accept arguments.")
        ret = self.upgraded()
        assert_(ret == self.was_upgraded, "wsgi.upgraded is incorrect.")
        return ret


def validator(application):

    def lint_app(*args, **kwargs):
        assert_(len(args) == 1, "Only a single argument is allowed.")
        assert_(not kwargs, "No keyword arguments are allowed.")
        environ = args[0]

        check_environ(environ)
        environ["http.body"] = InputValidator(environ["http.body"])
        environ["wsgi.errors"] = OutputValidator(environ["wsgi.errors"])
        
        upgrade_validator = UpgradeValidator(environ)
        environ["wsgi.upgrade"] = upgrade_validator.upgrade
        environ["wsgi.upgraded"] = upgrade_validator.upgraded
        
        resp = application(environ)
        if environ["wsgi.upgraded"]:
            assert_(resp in (True, False), "Invalid respones after upgrade.")
            return resp
        
        assert_(type(resp) is type((1,)), "Invalid response type.")
        assert_(len(resp) == 3, "Response is not a three-tuple.")
        check_status(resp[0])
        check_headers(resp[1])
        return (resp[0], resp[1], IteratorValidator(resp[2]))

    return lint_app

