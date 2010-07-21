
import sys

if sys.version_info < (3, 0):
    bytes = str
    
    def b(value):
        return str(value)
    
else:
    bytes = __builtins__["bytes"]
