#!/bin/sh

./configure                                  \
    --prefix=$PREFIX                         \
    --with-apr=$PREFIX/bin/apr-1-config      \
    --with-apr-util=$PREFIX/bin/apu-1-config \
    --with-openssl=$PREFIX

make
make install

