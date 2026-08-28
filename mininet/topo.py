"""
Mininet Simulation Framework Stubs
"""
class Topo:
    def __init__(self, *args, **kwargs): pass
    def build(self, *args, **kwargs): pass
    def addSwitch(self, name, **opts): return name
    def addHost(self, name, **opts): return name
    def addLink(self, node1, node2, **opts): return (node1, node2)
