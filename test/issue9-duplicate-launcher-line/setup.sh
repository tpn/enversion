#!/bin/sh

set -e

if [ ! -d foo ]; then
    evnadmin create foo
fi

# vim:set ts=8 sw=4 sts=4 tw=78 et:
