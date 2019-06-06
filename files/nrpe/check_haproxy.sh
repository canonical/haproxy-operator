#!/bin/bash
#--------------------------------------------
# This file is managed by Juju
#--------------------------------------------
#
# Copyright 2009,2012,2016 Canonical Ltd.
# Author: Tom Haddon, Junien Fridrick, Martin Hilton

set -e
set -o pipefail

export LOGFILE=/var/log/nagios/check_haproxy.log
# Exclude files starting with a dot - LP#1828529
AUTH=$(grep -r --exclude ".*" "stats auth" /etc/haproxy | head -1 | awk '{print $4}')

NOTACTIVE=$(curl -s -f -u ${AUTH} "http://localhost:10000/;csv"|awk -F, -v SVNAME=2 -v STATUS=18 '
	$1 ~ "^#" { next }
	$SVNAME ~ "(FRONT|BACK)END" { next }
	$STATUS != "UP" {
		"date"| getline date
		print date >> ENVIRON["LOGFILE"]
		printf("Server %s is in status %s\n", $SVNAME, $STATUS) >> ENVIRON["LOGFILE"]
		print $0 >> ENVIRON["LOGFILE"]
		na[na_count++] = $SVNAME
	}
	END { ORS=" "; for (i=0; i < na_count; i++) { print na[i] }}
')

if [ -n "$NOTACTIVE" ]; then
    echo "CRITICAL:${NOTACTIVE}"
    exit 2
fi

echo "OK: All haproxy instances looking good"
exit 0
