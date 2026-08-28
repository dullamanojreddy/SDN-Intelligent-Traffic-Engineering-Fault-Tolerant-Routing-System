"""Mininet Node Stubs"""
class Node:
    def __init__(self, name, **params):
        self.name = name
        self.params = params

class RemoteController(Node):
    pass

class OVSSwitch(Node):
    pass

class Host(Node):
    pass
