#!/bin/sh

./configure                               \
    --prefix=$PREFIX                      \
    --with-apr=$PREFIX/bin/apr-1-config   \
    --with-apr-iconv=$PREFIX/bin/apriconv \
    --with-expat=$PREFIX                  \
    --with-openssl=$PREFIX                \
    --with-sqlite3=$PREFIX                \
    --without-berkeley-db                 \
    --without-sqlite2                     \
    --without-freetds                     \
    --without-oracle                      \
    --without-pgsql                       \
    --without-odbc

make
make install

