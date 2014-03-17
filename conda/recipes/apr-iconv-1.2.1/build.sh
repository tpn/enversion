#!/bin/sh

./configure --prefix=$PREFIX --with-apr=$PREFIX
make
make install

