#!/usr/bin/env python3
"""
Basic Redundant Diamond Mininet Topology
             S2
            /  \
H1 ── S1 ─        ─ S4 ── H4
            \  /
             S3
"""
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info

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
