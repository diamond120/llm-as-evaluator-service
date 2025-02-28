#!/bin/bash

set -e

# Start Supervisor
/usr/bin/supervisord -c /etc/supervisor/supervisord.conf &

sleep 4

# Tail all log files in /var/log
tail -f /var/log/*.log
