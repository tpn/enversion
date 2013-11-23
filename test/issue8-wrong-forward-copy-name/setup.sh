#!/bin/sh

set -e

if [ ! -d foo ]; then
    evnadmin create foo
fi
svn mkdir -m "Initializing repository." file://`pwd`/foo/trunk
svn co file://`pwd`/foo foo.wc
cd foo.wc
svn mkdir branches tags
svn ci -m "Initializing repository."
cd trunk
date > date.txt
svn add date.txt
svn ci -m "Adding date.txt."
cd ..
svn up
cd branches
svn cp ../trunk 1.x
svn ci -m "Branching trunk to 1.x."
cd ../..
svn cp -m "Branching trunk to 2.x." file://`pwd`/foo/trunk \
                                    file://`pwd`/foo/branches/2.x


# vim:set ts=8 sw=4 sts=4 tw=78 et:
