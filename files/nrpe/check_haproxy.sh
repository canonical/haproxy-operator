#!/bin/bash
#--------------------------------------------
# This file is managed by Juju
#--------------------------------------------
#
# Copyright 2009,2012,2016 Canonical Ltd.
# Author: Tom Haddon, Junien Fridrick, Martin Hilton
#
# This script checks haproxy stats page and reports proxies or services that
# are down.
#
# Usage: "check_haproxy.sh -c monitoring_always_critical"
#   monitoring_always_critical: True (default) or False
#     Report a backend that is down always as critical. If false it will only
#     report a warning if there are still working services for that proxy.

set -e
set -o pipefail

monitoring_always_critical=True
while getopts c: flag
do
    case "${flag}" in
        c) monitoring_always_critical=${OPTARG};;
    esac
done

export LOGFILE=/var/log/nagios/check_haproxy.log
# Exclude files starting with a dot - LP#1828529
AUTH=$(grep -r --exclude ".*" "stats auth" /etc/haproxy | awk '{print $4; exit}')

if [ -z "$AUTH" ]; then
    echo "CRITICAL: unable to find credentials to query the haproxy statistics page"
    exit 2
fi

NOTACTIVE=$(curl -s -f -u ${AUTH} "http://localhost:10000/;csv"|awk -F, -v PXNAME=1 -v SVNAME=2 -v STATUS=18 '
  $1 ~ "^#" { next }
  $SVNAME ~ "(FRONT|BACK)END" && $STATUS == "DOWN" {
    px[px_count++] = $PXNAME; next
  }
  $SVNAME ~ "(FRONT|BACK)END" && $STATUS != "DOWN" {
    next
  }
  $STATUS != "UP" {
    "date"| getline date
    print date >> ENVIRON["LOGFILE"]
    printf("Server %s is in status %s\n", $SVNAME, $STATUS) >> ENVIRON["LOGFILE"]
    print $0 >> ENVIRON["LOGFILE"]
    na[na_count++] = $SVNAME
  }
  END {
    ORS="";
    if (px_count > 0) {
      print "Proxies DOWN: [";
      for (i=0; i < px_count; i++) {
        print px[i];
        if (i < px_count - 1) {
          print ", ";
        }
      };
      print "]; "
    }

    if (na_count > 0) {
      print "Services DOWN: [";
      for (i=0; i < na_count; i++) {
        print na[i];
        if (i < na_count - 1) {
          print ", ";
        }
      };
      print "];"
    }
  }
')


if [[ $NOTACTIVE == *"Proxies DOWN"* ]]; then
    echo "CRITICAL: ${NOTACTIVE}"
    exit 2
fi

if  [[ $NOTACTIVE == *"Services DOWN"* ]]; then
    if [[ "$monitoring_always_critical" == "False" ]]; then
        echo "WARNING: ${NOTACTIVE}"
        exit 1
    fi
    echo "CRITICAL: ${NOTACTIVE}"
    exit 2
fi

echo "OK: All haproxy instances looking good"
exit 0
