# SDN-ITE Demonstration Guide

This guide uses the currently verified startup and test commands. Run each
command without copying the shell or `mininet>` prompt shown before it.

## Recommended startup: controller and Mininet in WSL

This is the verified arrangement because the controller and Mininet use
`127.0.0.1:6653` in the same WSL environment.

### WSL terminal 1: controller

```bash
cd "/mnt/c/Users/D Manoj Reddy/Desktop/sdn"
source .venv-linux/bin/activate
python -m controller.app
```

Leave this terminal running.

### Windows PowerShell terminal 2: backend

```powershell
cd "C:\Users\D Manoj Reddy\Desktop\sdn"
.\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload --port 8000
```

Leave this terminal running.

### Windows PowerShell terminal 3: frontend

```powershell
cd "C:\Users\D Manoj Reddy\Desktop\sdn\frontend"
npm run dev
```

Open <http://localhost:5173>.

### WSL terminal 4: Mininet

```bash
cd "/mnt/c/Users/D Manoj Reddy/Desktop/sdn"
source .venv-linux/bin/activate
sudo mn -c
sudo -E python3 network/topologies/mesh.py
```

Wait for:

```text
*** Starting CLI:
mininet>
```

## Mininet verification commands

Run these inside the Mininet CLI. Do not type `mininet>` yourself.

```text
nodes
net
sh ovs-vsctl get Controller s1 is_connected
pingall
h1 ping -c 10 h7
sh ovs-ofctl -O OpenFlow13 dump-flows s1
```

The healthy baseline should show:

```text
*** Results: 0% dropped (12/12 received)
```

## Link-failure and failover test

Disable both ends of the `s1-s2` link:

```text
sh ip link set dev s1-eth1 down
sh ip link set dev s2-eth1 down
```

Verify the interfaces:

```text
sh ip link show dev s1-eth1
sh ip link show dev s2-eth1
sh ovs-ofctl -O OpenFlow13 show s1
```

Test the alternate route:

```text
h1 ping -c 10 h7
pingall
```

The expected result is still 0% packet loss. The dashboard should show the
failed `s1-s2` link in red after the backend refreshes its topology data.

Restore both interfaces after the test:

```text
sh ip link set dev s1-eth1 up
sh ip link set dev s2-eth1 up
```

## Alternative: controller running on Windows

Use this only if the controller is not running in WSL. The WSL Mininet
process must connect to the Windows host address, not `127.0.0.1`.

In Windows PowerShell, find the host IPv4 address:

```powershell
ipconfig
```

Start the controller in PowerShell:

```powershell
cd "C:\Users\D Manoj Reddy\Desktop\sdn"
.\.venv\Scripts\Activate.ps1
python -m controller.app
```

In WSL, replace `<WINDOWS_HOST_IP>` with the Windows IPv4 address:

```bash
cd "/mnt/c/Users/D Manoj Reddy/Desktop/sdn"
export SDN_CONTROLLER_IP=<WINDOWS_HOST_IP>
sudo -E python3 network/topologies/mesh.py
```

The controller must listen on `0.0.0.0:6653`, and Windows Firewall must allow
TCP port `6653` from WSL.

## Command rules

- Do not paste `mininet>` into the Mininet CLI.
- Run one command at a time.
- Use `ip link show` and `ovs-ofctl show` as the authoritative link-state
  checks. Mininet's `links` display may remain `OK OK` after a manual
  interface shutdown.
- Stop Mininet with `exit`, then clean stale state before the next run:

```bash
sudo mn -c
```
