#!/bin/sh

EXPAT=$PREFIX/include:$PREFIX/lib:expat

./configure                                        \
    --prefix=$PREFIX                               \
    --enable-optimize                              \
    --with-apr=$PREFIX/bin/apr-1-config            \
    --with-apr-util=$PREFIX/bin/apu-1-config       \
    --with-ctypesgen=$PREFIX/bin/ctypesgen.py      \
    --with-expat=$PREFIX/include:$PREFIX/lib:expat \
    --with-apxs=$PREFIX/bin/apxs                   \
    --with-apache-libexecdir=$PREFIX/modules       \
    --with-sqlite=$PREFIX                          \
    --with-openssl=$PREFIX                         \
    --with-zlib=$PREFIX                            \
    --without-berkeley-db

make
make swig-py
make ctypes-python

#make check
#make check-swig-py
#make check-ctypes-python

make install
make install-swig-py
make install-ctypes-python

mv $PREFIX/lib/svn-python/libsvn $SP_DIR
mv $PREFIX/lib/svn-python/svn $SP_DIR
rm -rf $PREFIX/lib/svn-python

