#!/bin/bash
#--------------------------------------------
# This file is managed by Juju
#--------------------------------------------
#
# Copyright 2009,2012,2016 Canonical Ltd.
# Author: Tom Haddon, Junien Fridrick

set -e

CRITICAL=0
NOTACTIVE=''
LOGFILE=/var/log/nagios/check_haproxy.log
AUTH=$(grep "stats auth" /etc/haproxy/haproxy.cfg | head -1 | awk '{print $4}')
SSL=$(grep 10000 /etc/haproxy/haproxy.cfg | grep -q ssl && echo "-S" || true)
HAPROXY_SOCKET=/var/run/haproxy.user.sock

# columns with service name and service status in the CSV output
NAME_COL=2
STATUS_COL=18

for line in $(echo 'show stat'|socat $HAPROXY_SOCKET stdio|egrep -v '^#'|cut -d, -f$NAME_COL,$STATUS_COL); do
    IFS=','
    set $line
    appserver=$1
    state=$2
    case $appserver in
       # ignore the FRONTEND and BACKEND servers
        FRONTEND|BACKEND) continue;;
        *) if [ "$state" != "UP" ]; then
               date >> $LOGFILE
               echo "Server $appserver is in status $state" >> $LOGFILE
               /usr/lib/nagios/plugins/check_http ${SSL} -a ${AUTH} -I 127.0.0.1 -p 10000 -v | grep $appserver >> $LOGFILE 2>&1
               CRITICAL=1
               NOTACTIVE="${NOTACTIVE} $appserver"
          fi
    esac
done

if [ $CRITICAL = 1 ]; then
    echo "CRITICAL:${NOTACTIVE}"
    exit 2
fi

echo "OK: All haproxy instances looking good"
exit 0
