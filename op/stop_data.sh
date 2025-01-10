#!/bin/sh

set -e
supervisorctl -c ./op/supervisord.conf shutdown
