#!/bin/sh
# How the tests are run in Jenkins by Tarmac

set -e

DOWNLOAD_CACHE=$(dirname `dirname $PWD`)/download-cache
DOWNLOAD_CACHE_BRANCH=~diogobaeder/canonical-marshal/download-cache

if [ -d $DOWNLOAD_CACHE ]; then
    echo "Updating download cache at dir" $DOWNLOAD_CACHE
    bzr pull -d $DOWNLOAD_CACHE --overwrite
else
    echo "Branching the download cache in dir" $DOWNLOAD_CACHE
    bzr branch lp:$DOWNLOAD_CACHE_BRANCH $DOWNLOAD_CACHE
fi

fab bootstrap:download_cache_path=$DOWNLOAD_CACHE
fab test
