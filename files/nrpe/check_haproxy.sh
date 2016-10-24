#!/bin/bash
#--------------------------------------------
# This file is managed by Juju
#--------------------------------------------
#
# Copyright 2009,2012,2016 Canonical Ltd.
# Author: Tom Haddon, Junien Fridrick, Martin Hilton

set -e

export LOGFILE=/var/log/nagios/check_haproxy.log
HAPROXY_SOCKET=$(grep "stats socket" /etc/haproxy/haproxy.cfg | head -1 | awk '{print $3}')

if [ -z "$HAPROXY_SOCKET" ]; then
    echo "CRITICAL: no stats socket"
    exit 2
fi

# In the following script $2 is the server name and $18 is the status.
NOTACTIVE=$(echo 'show stat'|socat $HAPROXY_SOCKET stdio|awk -F, '
	BEGIN { na_count=0 }
	$1 ~ "^#" { next }
	$2 ~ "(FRONT|BACK)END" { next }
	$18 != "UP" {
		printf("Server %s is in status %s\n", $2, $18) >> ENVIRON["LOGFILE"]
		print $0 >> ENVIRON["LOGFILE"]
		na[na_count] = $2
		na_count++
	}
	END { ORS=" "; for (i=0; i < na_count; i++) { print na[i] }}
')

if [ -n "$NOTACTIVE" ]; then
    echo "CRITICAL:${NOTACTIVE}"
    exit 2
fi

echo "OK: All haproxy instances looking good"
exit 0
