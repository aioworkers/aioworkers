#!/bin/sh
set -e

COMMAND="python -m aioworkers.cli -c config.yaml -l info -g"

if [ "$1" = 'ping' ]; then
    exec ${COMMAND} ping start
fi

if [ "$1" = 'pong' ]; then
    exec ${COMMAND} pong
fi

if [ "$1" = '--help' ]; then
    echo "Specify application: ping or pong."
fi
