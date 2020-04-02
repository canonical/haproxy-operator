#!/bin/bash
#--------------------------------------------
# This file is managed by Juju
#--------------------------------------------
#                                       
# Copyright 2009,2012 Canonical Ltd.
# Author: Tom Haddon

# These should be config options at some stage
CURRQthrsh=0
MAXQthrsh=100

# Exclude files starting with a dot - LP#1828529
AUTH=$(grep -r --exclude ".*" "stats auth" /etc/haproxy | head -1 | awk '{print $4}')

if [ -z "$AUTH" ]; then
    echo "CRITICAL: unable to find credentials to query the haproxy statistics page"
    exit 2
fi

HAPROXYSTATS=$(/usr/lib/nagios/plugins/check_http -a ${AUTH} -I 127.0.0.1 -p 10000 -u '/;csv' -v)

for BACKEND in $(echo $HAPROXYSTATS| xargs -n1 | grep BACKEND | awk -F , '{print $1}')
do
    CURRQ=$(echo "$HAPROXYSTATS" | grep ^$BACKEND, | grep BACKEND | cut -d , -f 3)
    MAXQ=$(echo "$HAPROXYSTATS"  | grep ^$BACKEND, | grep BACKEND | cut -d , -f 4)

    if [[ $CURRQ -gt $CURRQthrsh ]] ; then
        echo "CRITICAL: queue depth for $BACKEND - CURRENT:$CURRQ"
        exit 2
    fi
    if [[ $MAXQ -gt $MAXQthrsh ]] ; then
        echo "CRITICAL: max queue depth for $BACKEND - $MAXQ is over threshold ($MAXQthrsh). After fixing, reload haproxy to clear alert by resetting max queue depth counter to 0."
        exit 2
    fi
done

echo "OK: All haproxy queue depths looking good"
exit 0

