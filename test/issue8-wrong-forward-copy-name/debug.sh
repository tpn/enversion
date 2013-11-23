#!/bin/sh

set -e

../cleanup.sh
svnadmin create foo
. setup.sh
evnadmin analyze foo


# vim:set ts=8 sw=4 sts=4 tw=78 et:
