"""Mininet CLI & Log Stubs"""
def CLI(net):
    pass

def setLogLevel(level):
    pass

def info(msg, *args, **kwargs):
    print(msg % args if args else msg, end="")
