#!/bin/sh

EXPAT=$PREFIX/include:$PREFIX/lib:expat

./configure                                        \
    --prefix=$PREFIX                               \
    --enable-ssl                                   \
    --enable-mods-shared=all                       \
    --enable-authn-alias=shared                    \
    --enable-cache                                 \
    --enable-disk_cache                            \
    --enable-file_cache                            \
    --enable-mem_cache                             \
    --enable-deflate                               \
    --enable-proxy                                 \
    --enable-proxy-connect                         \
    --enable-proxy-http                            \
    --enable-proxy-ftp                             \
    --enable-so                                    \
    --enable-rewrite                               \
    --enable-dav                                   \
    --enable-logio                                 \
    --enable-headers                               \
    --enable-expires                               \
    --enable-mime-magic                            \
    --enable-speling                               \
    --enable-auth-digest                           \
    --enable-pie                                   \
    --enable-info                                  \
    --enable-dav-fs                                \
    --enable-dav-lock                              \
    --enable-vhost-alias                           \
    --with-z=$PREFIX                               \
    --with-pcre=$PREFIX                            \
    --with-openssl=$PREFIX                         \
    --with-expat=$PREFIX/include:$PREFIX/lib:expat \
    --with-apr=$PREFIX/bin/apr-1-config            \
    --with-apr-util=$PREFIX/bin/apu-1-config

make
make install
