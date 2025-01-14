#!/bin/sh

set -e
supervisorctl -c ./op/supervisord_data.conf shutdown
