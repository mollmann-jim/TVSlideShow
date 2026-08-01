#!/usr/bin/env python3

# Jim Mollmann
import os
import sys

def getDIBval(image, offset, length):
    DIBoff = 14
    start  = DIBoff + offset
    end    = start  + length
    return int.from_bytes(image[start : end], byteorder="little")

def extract_image_from_bmp(image):
    pos   = 0
    pos = image.find(b'BM', pos)
    #print(pos)
    # Extract size from BMP header (4 bytes starting at offset 2, little-endian)
    fileSize = int.from_bytes(image[pos + 2 : pos + 6], byteorder="little")
    #print('fileSize:', fileSize)
    pixelOffset = int.from_bytes(image[pos + 10 : pos + 14], byteorder="little")
    #print('pixelOffset:', pixelOffset)
    DIBoff = 14
    DIBsize   = getDIBval(image,  0, 4)
    #print('DIBsize:', DIBsize)
    width     = getDIBval(image,  4, 4)
    height    = getDIBval(image,  8, 4)
    #print('width x height:', width, ' x ', height)
    planes    = getDIBval(image, 12, 2)
    bitsPix   = getDIBval(image, 14, 2)
    compress  = getDIBval(image, 16, 4)
    imageSize = getDIBval(image, 20, 4)
    #print('planes:', planes, 'bitsPix:', bitsPix, 'compress:', compress,
          'imageSize:', imageSize)
    rowLen    = int(width * bitsPix / 8)
    #print('rowLen:', rowLen)
    padRowLen = int((rowLen + 3) / 4 ) * 4
    #print('padRowLen:', padRowLen)
    print('imageSize:', imageSize, 'imageBytes:', padRowLen * height)
    pixels = b''
    print(type(image), type(pixelOffset), type(rowLen), type(pixels))
    for row in range(height):
        pixels += image[pixelOffset : pixelOffset + rowLen]
        pixelOffset += padRowLen
    print('len(pixels):', len(pixels))
    
def main():
    if len(sys.argv) > 1:
        fileName = sys.argv[1]
    else:
        fileName = 'foo.bmp'
    
    with open(fileName, 'rb') as image_file:
        image = image_file.read()
    print(len(image))
    extract_image_from_bmp(image)


if __name__ == '__main__':
    # want unbuffered stdout for use with "tee"
    buffered = os.getenv('PYTHONUNBUFFERED')
    if buffered is None:
        myenv = os.environ.copy()
        myenv['PYTHONUNBUFFERED'] = 'Please'
        os.execve(sys.argv[0], sys.argv, myenv)
    main()
