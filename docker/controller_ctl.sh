#!/bin/bash
# Start/stop one controller instance in the bench container:  controller_ctl.sh primary|standby start|stop
set -e
export CONTROLLER_API_TOKEN="${CONTROLLER_API_TOKEN:-bench-token}" PYTHONDONTWRITEBYTECODE=1
who=$1; action=$2
if [ "$who" = primary ]; then OF=6653; REST=8080; PEER=8081; else OF=6654; REST=8081; PEER=8080; fi
pidfile=/root/$who.pid
case "$action" in
  start)
    cd /work
    CONTROLLER_OF_PORT=$OF CONTROLLER_REST_PORT=$REST CONTROLLER_ID=$who CONTROLLER_ROLE=$who \
      CONTROLLER_PEER_API_URL=http://127.0.0.1:$PEER CONTROLLER_HA_INTERVAL_SEC=0.5 \
      CONTROLLER_HA_FAILURE_THRESHOLD=3 CONTROLLER_HA_RECOVERY_THRESHOLD=2 \
      nohup python3 -m controller.app >> /root/$who.log 2>&1 &
    echo $! > $pidfile ;;
  stop)
    [ -f $pidfile ] && kill -9 $(cat $pidfile) 2>/dev/null || true
    rm -f $pidfile ;;
esac
