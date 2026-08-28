#!/usr/bin/env python3
"""
Multi-Path Fault-Tolerant Mesh Mininet Topology
                 S2 (100M) ─────── S5 (100M)
                /   \             /   \
               /     \           /     \
H1, H2 ── S1 (100M)    S4 (100M)        S7 ── H7, H8
               \     /           \     /
                \   /             \   /
                 S3 (100M) ─────── S6 (100M)
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

class MultiPathMeshTopo(Topo):
    def build(self):
        # 7 Switches (S1 - S7)
        switches = {}
        for i in range(1, 8):
            dpid = f"{i:016x}"
            switches[f's{i}'] = self.addSwitch(f's{i}', dpid=dpid, protocols='OpenFlow13')

        # Hosts
        h1 = self.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
        h2 = self.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')
        h7 = self.addHost('h7', ip='10.0.0.7/24', mac='00:00:00:00:00:07')
        h8 = self.addHost('h8', ip='10.0.0.8/24', mac='00:00:00:00:00:08')

        # Connect Hosts
        self.addLink(h1, switches['s1'], port2=3)
        self.addLink(h2, switches['s1'], port2=4)
        self.addLink(h7, switches['s7'], port2=4)
        self.addLink(h8, switches['s7'], port2=5)

        # Switch Links with Bandwidth & Delay Attributes
        # S1 connections
        self.addLink(switches['s1'], switches['s2'], port1=1, port2=1, bw=100, delay='5ms')
        self.addLink(switches['s1'], switches['s3'], port1=2, port2=1, bw=100, delay='5ms')

        # Layer 1 to Layer 2
        self.addLink(switches['s2'], switches['s4'], port1=2, port2=1, bw=100, delay='6ms')
        self.addLink(switches['s2'], switches['s5'], port1=3, port2=1, bw=100, delay='5ms')
        self.addLink(switches['s3'], switches['s4'], port1=2, port2=2, bw=100, delay='6ms')
        self.addLink(switches['s3'], switches['s6'], port1=3, port2=1, bw=100, delay='5ms')

        # Layer 2 to S7 (Egress)
        self.addLink(switches['s4'], switches['s7'], port1=3, port2=1, bw=100, delay='5ms')
        self.addLink(switches['s5'], switches['s7'], port1=2, port2=2, bw=100, delay='5ms')
        self.addLink(switches['s6'], switches['s7'], port1=2, port2=3, bw=100, delay='5ms')

def run():
    if not MININET_AVAILABLE or Mininet is None:
        print("Mininet is required to run this topology script (Linux/WSL2).")
        return
    setLogLevel('info')
    topo = MultiPathMeshTopo()
    net = Mininet(
        topo=topo,
        switch=OVSSwitch,
        controller=RemoteController('c0', ip='127.0.0.1', port=6653),
        link=TCLink,
        autoSetMacs=True
    )
    net.start()
    info("*** Multi-Path Mesh Network Started with 7 Open vSwitches & OpenFlow 1.3\n")
    CLI(net)
    net.stop()

if __name__ == '__main__':
    run()
