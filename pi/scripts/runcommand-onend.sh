#!/bin/bash
{
  echo "==== onend $(date) ===="
  echo "PWD=$PWD"
  echo "USER=$(whoami)"
  echo "ARGS: $@"
} >> /tmp/pistation_hook.log

export PISTATION_MODE="end"
python3 /home/pi/pistation/session_logger.py "$@" >> /tmp/pistation_hook.log 2>&1
echo "" >> /tmp/pistation_hook.log
