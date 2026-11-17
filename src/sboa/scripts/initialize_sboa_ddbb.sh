#!/bin/bash
# Reset the scheduler database in the dedicated development/test environment.
set -euo pipefail
exec sboa_init.py -y "$@"
