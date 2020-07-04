#!/bin/bash
set -x
PI="192.168.123.12"
cd /home/jim/tools/TVSlideShow/makeDB
time  ./TVslide.image.copy.db
cd /home/jim/tools/TVSlideShow/imbedImage
time ./imbedImages.copy.py
time ssh $PI /home/jim/bin/copy.DB
