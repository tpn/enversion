#!/bin/sh

./configure                                     \
    --prefix=$PREFIX                            \
    --with-installbuilddir=$PREFIX/apr-1/build

make
make install

