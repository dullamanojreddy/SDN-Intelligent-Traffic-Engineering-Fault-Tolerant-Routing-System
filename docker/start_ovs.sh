#!/bin/bash
# Start Open vSwitch inside the bench container. Docker Desktop's VM has no
# openvswitch kernel module, so we run ovsdb + ovs-vswitchd manually and use the
# userspace (netdev) datapath (SDN_OVS_DATAPATH=user).
set -e
mkdir -p /var/run/openvswitch /var/log/openvswitch /etc/openvswitch
[ -f /etc/openvswitch/conf.db ] || ovsdb-tool create /etc/openvswitch/conf.db /usr/share/openvswitch/vswitch.ovsschema
ovsdb-server /etc/openvswitch/conf.db --remote=punix:/var/run/openvswitch/db.sock \
    --pidfile --detach --log-file=/var/log/openvswitch/ovsdb-server.log
ovs-vsctl --no-wait init
ovs-vswitchd unix:/var/run/openvswitch/db.sock --pidfile --detach --log-file=/var/log/openvswitch/ovs-vswitchd.log
for _ in $(seq 1 20); do ovs-vsctl --timeout=2 show >/dev/null 2>&1 && break; sleep 0.5; done
echo "OVS ready: $(ovs-vsctl --version | head -1)"
