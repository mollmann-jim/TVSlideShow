#!/usr/bin/env python3

# Jim Mollmann
import os
import sys
import sqlite3
import datetime
import subprocess

def adapt_datetime(dt):
    return datetime.isoformat(sep=' ').replace('T', ' ')

def convert_datetime(val):
    return datetime.datetime.fromisoformat(val)

class DB:
    def __init__(self, debug = True):
        self.debug   = debug
        self.picRoot = '/home/jim/pictures/'
        self.DB      = '/home/jim/tools/TVSlideShow.py/TVSlides.sql'
        self.DB      = '/home/jim/tools/TVSlideShow.py/TVSlides.sql.20260731'
        self.DBtable = 'pictures'
        sqlite3.register_adapter(datetime.datetime, adapt_datetime)
        sqlite3.register_converter("DATETIME", convert_datetime)
        self.db      = sqlite3.connect(self.DB, detect_types=sqlite3.PARSE_DECLTYPES)
        self.c       = self.db.cursor()

    def getBDayInfo(self):
        self.birthdays = {}
        self.bDays     = []
        select = 'SELECT birthday, filename FROM '         \
            ' ( SELECT birthday, filename, count(*) OVER ' \
            ' ( PARTITION BY birthday ) '                  \
            ' AS cnt FROM pictures ) '                     \
            ' WHERE cnt > 1;'
        self.c.execute(select)
        fileCnt = 0
        for row in self.c:
            birthday, filename = row
            if birthday not in self.birthdays:
                self.birthdays[birthday] = []
            self.birthdays[birthday].append(self.picRoot + filename)
            fileCnt += 1
        self.bDays = list(self.birthdays)
        print(f'DB:getBDayInfo:birthdays: {len(self.birthdays):5d} files: {fileCnt:6d}')

    def nextBDay(self):
        if len(self.bDays) > 0:
            nextBD = self.bDays.pop()
            return self.birthdays[nextBD]
        return None

class Images:
    def __init__(self, debug = True):
        self.debug  = debug
        self.resize = ' -resize 256x256 '
        if self.debug:
            self.resize = ' -resize 32x32 '
            
    def toBMP(self, filename):
        try:
            with open(filename, 'rb') as imageFile:
                image = imageFile.read()
        except:
            return None
        ext = filename.split('.')[-1].lower()
        isPEF =  ext == 'pef'
        isTIF =  ext == 'tif'
        inQual = inNum = ''
        if isPEF:
            inQual = 'PEF:'
        if isTIF:
            inNum = '[0]'
        cmd = 'magick ' + inQual + '-' + inNum + self.resize + 'bmp:-'
        #print(cmd)
        result = doCmd(cmd, input = image)
        if result.returncode != 0:
            print('ABORT: toBMP: initial image:', filename)
            return False
        return result.stdout

    def bmp2Pixels(self, image):
        pos   = 0
        pos = image.find(b'BM', pos)
        if pos == -1:
            return False
        # Extract size from BMP header (4 bytes starting at offset 2, little-endian)
        fileSize = int.from_bytes(image[pos + 2 : pos + 6], byteorder="little")
        pixelOffset = int.from_bytes(image[pos + 10 : pos + 14], byteorder="little")
        #DIBoff = 14
        #DIBsize   = self.getDIBval(image,  0, 4)
        width     = self.getDIBval(image,  4, 4)
        height    = self.getDIBval(image,  8, 4)
        #planes    = self.getDIBval(image, 12, 2)
        bitsPix   = self.getDIBval(image, 14, 2)
        #compress  = self.getDIBval(image, 16, 4)
        imageSize = self.getDIBval(image, 20, 4)
        rowLen    = int(width * bitsPix / 8)
        padRowLen = int((rowLen + 3) / 4 ) * 4
        pixels = b''
        for row in range(height):
            pixels += image[pixelOffset : pixelOffset + rowLen]
            pixelOffset += padRowLen
        #print('bmp2Pixels:', len(pixels))
        return pixels    

    def pixelCompare(self, x, y):
        if x == y:
            return 'match'
        if len(x) != len(y):
            return f'length diff {len(x):8d} != {len(y):7d}'
        diff = 0
        for i in range(len(x)):
            #print(i, x[i], y[i])
            diff += abs(x[i] - y[i])
        return [diff, diff / len(x)]
   
        
    
    def getDIBval(self, image, offset, length):
        DIBoff = 14
        start  = DIBoff + offset
        end    = start  + length
        return int.from_bytes(image[start : end], byteorder="little")

    
def doCmd(command, printFailure = True, debug = False, input = None):
    if debug:
        print('doCmd:command:', command)
    result = subprocess.run(command, shell = True, stdout = subprocess.PIPE, \
                            stderr=subprocess.STDOUT, input = input, check = False)
    if debug:
        if result.stdout is not None:
            print('stdout:' + '\n' + result.stdout.decode('utf-8'))
        if result.stderr is not None:
            print('stderr:' + '\n' + result.stderr.decode('utf-8'))

    if result.returncode != 0 & printFailure:
        #print(result.stdout)
        print('Failed: RC:', result.returncode, command)
        print(result.stderr)
    if debug:
        print('doCmd:result:', result)
    return result

def doMV(src, dst):
    cmd = f'mv "{src:s}" "{dst:s}"'
    print('CMD:', cmd)
    doCmd(cmd)

def moveFromiPhone(a, b):
    iPhoneAll = '2026.06.21.All.iPhone'
    if iPhoneAll in a:
        return True, a, b
    if iPhoneAll in b:
        return True, b, a
    return False, a, b
    
    
def main():
    db = DB()
    db.getBDayInfo()
    image = Images()
    cnt = 0
    for fileList in iter(db.nextBDay, None):
        #print(len(fileList),fileList )
        cnt += 1
        if cnt > 1000000:
            break
        pixels = []
        fileCnt = 0
        for fileName in fileList:
            if os.path.isfile(fileName):
                fileCnt += 1
        if fileCnt < 2:
            continue
        for fileName in fileList:
            bmp = image.toBMP(fileName)
            if bmp is not None:
                pixel = image.bmp2Pixels(bmp)
                pixels.append(pixel)
        for i in range(len(pixels)):
            for j in range(i + 1, len(pixels)):
                result = image.pixelCompare(pixels[i], pixels[j])
                iFile = fileList[i][19:]
                jFile = fileList[j][19:]
                print(cnt, i, j, iFile, jFile, result)
                iPhone, src, dst = moveFromiPhone(fileList[i], fileList[j])
                if result == 'match':
                    if iPhone:
                        doMV(src, dst)
                    else:
                        print('NoPhoneMatch:', iFile, jFile)
                elif isinstance(result, list):
                    c = result[1]
                    if c<= 2.0:
                        if iPhone:
                            iExt = iFile.split('/')[-1]
                            jExt = jFile.split('/')[-1]
                            if iExt == jExt:
                                doMV(src, dst)
                                print(f'maybe:   {c:10.4f} - {iFile:s} {jFile:s}')
                            else:
                                print(f'mayhaps: {c:10.4f} - {iFile:s} {jFile:s}')

if __name__ == '__main__':
    # want unbuffered stdout for use with "tee"
    buffered = os.getenv('PYTHONUNBUFFERED')
    if buffered is None:
        myenv = os.environ.copy()
        myenv['PYTHONUNBUFFERED'] = 'Please'
        os.execve(sys.argv[0], sys.argv, myenv)
    main()
