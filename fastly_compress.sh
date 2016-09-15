#!/bin/bash

set -e

FASTLYDIR=/var/log/fastly
ROTATEDIR=$FASTLYDIR/rotated

mkdir -p $ROTATEDIR
for i in `find $FASTLYDIR -maxdepth 1 -type f -iname '*-*' -not -iname '*.gz' -mmin +1`; do
    gzip -q $i
done
for i in `find $FASTLYDIR -maxdepth 1 -type f -iname '*.gz'`; do
    mv $i $ROTATEDIR
done
