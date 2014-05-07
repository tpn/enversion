#!/bin/bash

SRC_DIR=$RECIPE_DIR/../../..

cd $SRC_DIR

$PYTHON distutils_setup.py install
