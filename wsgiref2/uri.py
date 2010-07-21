
import re
import traceback

from wsgiref2.util import b

class RegExNode(object):    
    def __init__(self, name=None):
        if name is None:
            self.name = b("?:")
        else:
            self.name = b("?P<") + b(name) + b(">")

    def compile(self):
        return re.compile(b("^") + self.render() + b("$"))

    def render(self):
        raise NotImplemented()

class Li(RegExNode): # Literal
    def __init__(self, byte):
        self.byte = b(byte)

    def render(self):
        return self.byte

class CC(object): # Character Class
    def __init__(self, bytes):
        self.bytes = b(bytes)

    def render(self):
        return b("[") + self.bytes + b("]")

class And(RegExNode):
    def __init__(self, *nodes, **params):
        super(And, self).__init__(**params)
        self.nodes = nodes

    def render(self):
        ret = [b("(") + self.name]
        for n in self.nodes:
            ret.append(n.render())
        ret.append(b(")"))
        return b("").join(ret)

class Or(RegExNode):
    def __init__(self, *nodes, **params):
        super(Or, self).__init__(**params)
        self.nodes = nodes

    def render(self):
        ret = [b("(") + self.name]
        for i, n in enumerate(self.nodes):
            ret.append(b("(?:") + n.render() + b(")"))
            if i+1 < len(self.nodes):
                ret.append(b("|"))
        ret.append(b(")"))
        return b("").join(ret)
        
class Rep(RegExNode): # Repeat N or more times
    def __init__(self, node, n=0, **params):
        super(Rep, self).__init__(**params)
        self.node = node
        if n == 0:
            self.n = b("*")
        elif n == 1:
            self.n = b("+")
        else:
            raise ValueError(n)

    def render(self):
        rep = b("(?:") + self.node.render() + b(")") + self.n
        return b("(") + self.name + rep + b(")")

class Opt(RegExNode):
    def __init__(self, node, **params):
        super(Opt, self).__init__(**params)
        self.node = node

    def render(self):
        return b("(") + self.name + self.node.render() + b(")?")

digit           = CC("0-9")
upalpha         = CC("A-Z")
lowalpha        = CC("a-z")
alpha           = CC("A-Za-z")
alphanum        = CC("0-9A-Za-z")
hexchar         = CC("0-9A-Fa-f")
escaped         = And(Li("%"), hexchar, hexchar)
mark            = CC("-_.!~*'()")
unreserved      = Or(alphanum, mark)
reserved        = CC(";/?:@&=+$,")
uric            = Or(reserved, unreserved, escaped)
fragment        = Rep(uric, name="fragment")
uri_fragment    = And(Li("#"), fragment)
query           = Rep(uric, name="query")
query_string    = And(Li("\?"), query)
pchar           = Or(unreserved, escaped, CC(":@&=+$,"))
param           = Rep(pchar)
segment         = And(Rep(pchar), Rep(And(Li(";"), param)))
path_segments   = And(segment, Rep(And(Li("/"), segment)))
abs_path        = And(Li("/"), path_segments, name="path")
port            = Rep(digit, name="port", n=1)
IPv4address     = And(Rep(digit, n=1), Li("\."), Rep(digit, n=1), Li("\."),
                        Rep(digit, n=1), Li("\."), Rep(digit, n=1), Li("\.")
                )
toplabel        = Or(alpha, And(alpha, Rep(Or(alphanum, Li("-"))), alphanum))
domainlabel     = Or(
                    alphanum,
                    And(alphanum, Rep(Or(alphanum, Li("-"))), alphanum)
                )
hostname        = And(Rep(And(domainlabel, Li("\."))), toplabel, Opt(Li("\.")))
host            = Or(hostname, IPv4address, name="host")
hostport        = And(host, Opt(And(Li(":"), port)))
userinfo        = Rep(Or(unreserved, escaped, CC(";:&=+$,")), name="userinfo")
server          = Opt(And(Opt(And(userinfo, Li("@"))), hostport))
scheme          = And(alpha, Rep(Or(alpha, digit, CC("+-."))), name="scheme")
absolute_uri    = And(
                    scheme,
                    Li("://"),
                    server,
                    Opt(abs_path),
                    Opt(query_string),
                    Opt(uri_fragment),
                    name="raw"
                )

patterns = [
    abs_path.compile(),
    absolute_uri.compile()
]

print absolute_uri.render()

def parse(value):
    if value == b("*"):
        return {b("star"): b("*")}
    for pat in patterns:
        match = pat.match(value)
        if match:
            return match.groupdict()
    raise ValueError(b"Invalid HTTP URI: " + value)

