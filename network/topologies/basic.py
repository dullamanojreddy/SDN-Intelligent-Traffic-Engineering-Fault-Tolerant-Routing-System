#!/usr/bin/env python3
"""
Basic Redundant Diamond Mininet Topology
             S2
            /  \
H1 ── S1 ─        ─ S4 ── H4
            \  /
             S3
"""
import importlib

def _load_mininet():
    try:
        _topo = importlib.import_module("mininet.topo")
        _net = importlib.import_module("mininet.net")
        _node = importlib.import_module("mininet.node")
        _link = importlib.import_module("mininet.link")
        _cli = importlib.import_module("mininet.cli")
        _log = importlib.import_module("mininet.log")
        return (
            True,
            _topo.Topo,
            _net.Mininet,
            _node.RemoteController,
            _node.OVSSwitch,
            _link.TCLink,
            _cli.CLI,
            _log.setLogLevel,
            _log.info
        )
    except Exception:
        class DummyTopo:
            def addSwitch(self, *args, **kwargs):
                return args[0] if args else "s"
            def addHost(self, *args, **kwargs):
                return args[0] if args else "h"
            def addLink(self, *args, **kwargs):
                pass
        return False, DummyTopo, None, None, None, None, None, None, None

(
    MININET_AVAILABLE,
    Topo,
    Mininet,
    RemoteController,
    OVSSwitch,
    TCLink,
    CLI,
    setLogLevel,
    info
) = _load_mininet()

class BasicDiamondTopo(Topo):
    def build(self):
        # Add Switches
        s1 = self.addSwitch('s1', dpid='0000000000000001', protocols='OpenFlow13')
        s2 = self.addSwitch('s2', dpid='0000000000000002', protocols='OpenFlow13')
        s3 = self.addSwitch('s3', dpid='0000000000000003', protocols='OpenFlow13')
        s4 = self.addSwitch('s4', dpid='0000000000000004', protocols='OpenFlow13')

        # Add Hosts
        h1 = self.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
        h4 = self.addHost('h4', ip='10.0.0.4/24', mac='00:00:00:00:00:04')

        # Add Host-Switch Links
        self.addLink(h1, s1, port2=1)
        self.addLink(h4, s4, port2=1)

        # Add Switch-Switch Links (100 Mbps, 5ms delay)
        self.addLink(s1, s2, port1=2, port2=1, bw=100, delay='5ms')
        self.addLink(s1, s3, port1=3, port2=1, bw=100, delay='5ms')
        self.addLink(s2, s4, port1=2, port2=2, bw=100, delay='5ms')
        self.addLink(s3, s4, port1=2, port2=3, bw=100, delay='5ms')

def run():
    if not MININET_AVAILABLE or Mininet is None:
        print("Mininet is required to run this topology script (Linux/WSL2).")
        return
    setLogLevel('info')
    topo = BasicDiamondTopo()
    net = Mininet(
        topo=topo,
        switch=OVSSwitch,
        controller=RemoteController('c0', ip='127.0.0.1', port=6653),
        link=TCLink,
        autoSetMacs=True
    )
    net.start()
    info("*** Basic Diamond Network Started with OpenFlow 1.3 Controller at 127.0.0.1:6653\n")
    CLI(net)
    net.stop()

if __name__ == '__main__':
    run()
