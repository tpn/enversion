#!/bin/sh

set -e

../cleanup.sh
setup.sh
evnadmin root-info /trunk/ foo > actual.txt
diff -u actual.txt expected.txt

debug.sh
evnadmin root-info /trunk/ foo > actual.txt
diff -u actual.txt expected.txt

# vim:set ts=8 sw=4 sts=4 tw=78 et:
