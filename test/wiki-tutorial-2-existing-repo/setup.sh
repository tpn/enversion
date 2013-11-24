#!/bin/sh

set -e

svnadmin create foo
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
svn cp -m "Tagging 1.0." file://`pwd`/foo/branches/1.x \
                         file://`pwd`/foo/tags/1.0
svn up foo.wc
cd foo.wc/trunk
date > new-date.txt
svn add new-date.txt
svn ci -m "Adding new-date.txt to trunk."
cd ../branches/1.x
svn merge ^/trunk .
svn ci -m "Syncing with trunk."
cd ../2.x
svn cp ../../trunk/new-date.txt .
svn ci -m "Copying a file when I should be merging..."
cd ../..
svn up
cd tags
svn mkdir 1.0-dodgy
svn ci -m "Creating a tag directory manually."
svn up ..
svn cp ../trunk 1.1
svn ci -m "Creating a valid tag." 1.1
svn up
date > 1.1/modifying-tag-is-bad.txt
svn add 1.1/modifying-tag-is-bad.txt
svn ci -m "Modifying a tag is bad." 1.1
svn up
svn rm 1.1
svn ci -m "Deleting one is even worse." 1.1
cd ..
svn up

# vim:set ts=8 sw=4 sts=4 tw=78 et:
