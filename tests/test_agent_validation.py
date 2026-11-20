"""Network agent input validation and OVS dump parsing (no Mininet required)."""
import http.client
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "network"))   # agent imports ovs_flows by bare name
import agent  # noqa: E402
import ovs_flows  # noqa: E402


@pytest.mark.parametrize("value", ["5; rm -rf /", "10", True, [1], {"a": 1}, float("nan"), -1, 10 ** 9])
def test_numeric_fields_reject_strings_and_out_of_range_values(value):
    with pytest.raises(agent.AgentError):
        agent._num(value, "bw", 0.001, 100000)


def test_numeric_fields_accept_none_and_bounded_numbers():
    assert agent._num(None, "bw", 0, 1) is None
    assert agent._num(5, "bw", 0, 10) == 5.0
    with pytest.raises(agent.AgentError):
        agent._num(None, "interval", 0, 1, allow_none=False)


@pytest.mark.parametrize("ip", ["10.0.0.999", "10.0.0.1; reboot", "abc", "10.0.0", ""])
def test_invalid_ip_addresses_are_rejected(ip):
    with pytest.raises(agent.AgentError):
        agent._valid_ip(ip)
    assert agent._valid_ip("10.0.0.7/24") == "10.0.0.7"


def test_mac_and_name_patterns_block_shell_metacharacters():
    assert agent.MAC_RE.match("00:00:00:00:00:01")
    assert not agent.MAC_RE.match("00:00:00:00:00:01; id")
    assert agent.NAME_RE.match("s8") and not agent.NAME_RE.match("s8;id")
    assert not agent.NAME_RE.match("this-name-is-too-long-for-linux")


def test_agent_http_requires_the_token_and_refuses_to_start_without_one():
    with pytest.raises(RuntimeError):
        agent.serve(object(), "127.0.0.1", 0, "")

    class FakeAgent:
        def topology(self):
            return {"switches": [], "hosts": [], "links": []}

    server = agent.serve(FakeAgent(), "127.0.0.1", 0, "s3cret")
    try:
        port = server.server_address[1]
        for header, expected in (({}, 401), ({"Authorization": "Bearer wrong"}, 401),
                                 ({"Authorization": "Bearer s3cret"}, 200)):
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            conn.request("GET", "/topology", headers=header)
            response = conn.getresponse()
            assert response.status == expected
            if expected == 200:
                assert json.loads(response.read()) == {"switches": [], "hosts": [], "links": []}
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        conn.request("POST", "/links", body="{not json", headers={"Authorization": "Bearer s3cret"})
        assert conn.getresponse().status in (400, 500)
        conn.request("GET", "/nope", headers={"Authorization": "Bearer s3cret"})
    finally:
        server.shutdown()


DUMP = """\
 cookie=0x0, duration=6.1s, table=0, n_packets=3, n_bytes=294, idle_timeout=300, priority=100,ip,nw_dst=10.0.0.7 actions=output:2
 cookie=0x0, duration=6.1s, table=0, n_packets=0, n_bytes=0, idle_timeout=300, priority=100,arp,arp_tpa=10.0.0.7 actions=output:"s1-eth2"
 cookie=0x0, duration=9s, table=0, n_packets=5, n_bytes=1, priority=0 actions=CONTROLLER:65535
 cookie=0x0, duration=9s, table=0, n_packets=5, n_bytes=1, priority=5,ipv6 actions=drop
OFPST_FLOW reply (OF1.3) (xid=0x2):
"""


def test_ovs_dump_parser_extracts_matches_ports_and_counters():
    flows = ovs_flows.parse_dump_flows(DUMP, "s1")
    assert len(flows) == 4
    ip, arp, miss, v6 = flows
    assert (ip["priority"], ip["match"], ip["out_ports"], ip["n_packets"], ip["idle_timeout"]) == (100, {"nw_dst": "10.0.0.7"}, [2], 3, 300)
    assert arp["out_ports"] == [2] and arp["match"] == {"arp_tpa": "10.0.0.7"}      # named port -> number
    assert miss["to_controller"] and miss["priority"] == 0 and not miss["out_ports"]
    assert v6["drop"] and v6["protocols"] == ["ipv6"]
    assert all(f["switch"] == "s1" for f in flows)


def test_ovs_dump_parser_ignores_noise():
    assert ovs_flows.parse_dump_flows("garbage\n\nNXST_FLOW reply\n") == []
