#!/usr/bin/env python3

# Jim Mollmann
import datetime as dt
import time
import math
import sys
import getopt
import os
import subprocess
import string
import argparse
import sqlite3
from pathlib import Path
import itertools
import re

def adapt_datetime(dt):
    return dt.isoformat(sep=' ').replace('T', ' ')

def convert_datetime(val):
    return dt.datetime.fromisoformat(val)

class Pictures:
    def __init__(self):
        self.picRoot = '/home/jim/pictures/'
        self.DB = '/home/jim/tools/TVSlideShow.py/TVSlides.sql'
        self.DBtable = 'pictures'
        sqlite3.register_adapter(dt.datetime, adapt_datetime)
        sqlite3.register_converter("DATETIME", convert_datetime)
        self.db = sqlite3.connect(self.DB)
        self.c = self.db.cursor()

    def getPictureFiles(self):
        cntFilesInDir = {}
        filesInDir    = {}
        cull          = []
        flipLR        = []
        flipUD        = []
        L90           = []
        R180          = []
        R90           = []
        i = 0
        imageExt = ['*jpg', '*.jpeg', '*pef', '*tif', '*gif',
                    '*JPG', '*.JPEG', '*PEF', '*TIF', '*GIF']
        unwantedDirs = ['xvpics', 'allergy', '4sale', 'small', 'images',
                        'Jaye', 'test', 'Test2', 'Rotate', 'cull']
        picDirLen = len(self.picRoot)
        picturesDir = Path(self.picRoot)
        image_paths = itertools.chain.from_iterable(picturesDir.rglob(ext) for ext in imageExt)
        for picture in image_paths:
            directory = str(picture.parent)[picDirLen:] + '/'
            cntFilesInDir[directory] = cntFilesInDir.setdefault(directory, 0) + 1
            if directory not in filesInDir:
                filesInDir[directory] = []
            filesInDir[directory].append(str(picture.name))
            #print('dir: ', directory, cntFilesInDir[directory], filesInDir[directory])
        for dir in sorted(cntFilesInDir):
            for remove in unwantedDirs:
                if remove in dir:
                    del cntFilesInDir[dir]
                    del filesInDir[dir]
                    #print('removed:', dir)
                    break
        for dir in sorted(cntFilesInDir):   
            #print(f'{cntFilesInDir[dir]:6d} : {dir:s}')
            pass
        subDirs = []
        for dir1 in sorted(cntFilesInDir):
            if dir1 in subDirs:
                continue
            subDirDict = {k : v for k, v in cntFilesInDir.items() if k.startswith(dir1)}
            for dir2 in sorted(subDirDict):
                if dir1 == dir2:
                    continue
                subDirs.append(dir2)
                #print('dir1:', dir1, 'subdir:', dir2)
        #print('subDirs:', subDirs)
        for dir in subDirs:
            del cntFilesInDir[dir]
            del filesInDir[dir]
        '''
        for dir in sorted(filesInDir):
            for file in sorted(filesInDir[dir]):
                print(dir + file)
        '''
        cull   = self.getRotates('Cull')
        print('culls:', cull)
        flipLR = self.getRotates('FlipLR')
        print('flipLRs', flipLR)
        flipUD = self.getRotates('FlipUD')
        print('flipUDs:', flipUD)
        L90    = self.getRotates('L90')
        print('L90s:', L90)
        R180   = self.getRotates('R180')
        print('R180s:', R180)
        R90    = self.getRotates('R90')
        print('R90s:', R90)
        

    def getRotates(self, subDir):
        rotates = []
        rotateBase = self.picRoot + 'Rotate/' + subDir
        rotPath = Path(rotateBase)
        for rot in rotPath.rglob('*'):
            rotates.append(str(rot)[len(rotateBase) + 1 :])
        return rotates
            
        
class Images:
    def __init__(self):
        self.directory = '/home/jim/tools/TVSlideShow/imbedImage/'
        self.DBx = '/home/jim/tools/TVSlideShow/makeDB/TVslides.image.test.sql'
        self.DB = '/home/jim/tools/TVSlideShow/sql/TVslides.image.sql'
        #doCmd('cp -p ' + self.DBx + ' ' + self.DB)
        #doCmd('ln ' + self.DBx + ' ' + self.DB)
        self.DBtable = 'pictures'
        self.db = sqlite3.connect(self.DB)
        self.c = self.db.cursor()
        countrows = 'SELECT COUNT(*) FROM ' + self.DBtable + ';'
        self.c.execute(countrows)
        self.rows = self.c.fetchone()[0]
        print('rows:', self.rows)
        self.n = 0
        self.debug = 0

    def getPicture(self, id):
        select = 'SELECT filename, rotate, label, location FROM ' + self.DBtable + ' WHERE id = ' + str(id) + ';'
        if self.debug: print(select)
        self.c.execute(select)
        picture, rotate, label, location = self.c.fetchone()            
        when = datetime.datetime.now().replace(microsecond = 0)
        print('{0:^19s}: {1:6d}: {2:5d}: {3:48}'.\
              format(str(when), self.n, id, picture))
        self.n += 1
        return (picture, rotate, label)

    def buildPicture(self, id):
        picture, rotate, label = self.getPicture(id)
        if self.debug: print(picture, id)
        tgtFile = self.directory + 'slide.out.jpg'
        tgtFile2 = self.directory + 'slide.out-0.jpg'
        command = 'convert -auto-orient ' + rotate + '-resize 1720x1080 -quality 95 ' + \
            picture  + ' ' + tgtFile
        doCmd(command)
        
        if picture.split('.')[-1] == 'tif':
            command = 'mv ' + tgtFile2 + ' ' + tgtFile
            doCmd(command)
            
        labelText = self.directory + 'label.txt'
        with open(labelText, 'w') as Label:
            Label.write(label + '\n')
        labelImage = self.directory + 'label.jpg'
        # Raspberry Pi font
        command = 'convert -size 200x1080 -background grey  -fill black  -font helvetica '\
                  '-pointsize 10 label:@' + labelText + ' ' + labelImage
        # Fedora font
        command = 'convert -size 200x1080 -background grey  -fill black  -font NimbusSans-Regular '\
                  '-pointsize 10 label:@' + labelText + ' ' + labelImage
        doCmd(command)
        
        slideFile = self.directory + 'slide.jpg'
        command = 'convert -background grey ' + tgtFile + ' ' + labelImage + ' +append ' + slideFile
        doCmd(command)
        
        displayFile = self.directory + 'display.jpg'
        command = 'convert -resize 1920x1080 -quality 95 ' + slideFile + ' ' + displayFile
        doCmd(command)
        return displayFile

    def addImages(self):
        select = 'SELECT id FROM ' + self.DBtable + ' WHERE image is NULL;'
        self.c.execute(select)
        rows = self.c.fetchall()
        print(len(rows), "images to add")
        for row in rows:
            i = row[0]
            imageFile = self.buildPicture(i)
            if self.debug: print(i, imageFile)
            with open(imageFile, 'rb') as image_file:
                image = image_file.read()
            #update = 'UPDATE ' + self.DBtable + ' SET image = ? WHERE id = ' + str(i) + ' ;'
            update = 'UPDATE ' + self.DBtable + ' SET image = ? WHERE id = ? ;'
            if self.debug: print(update)
            self.c.execute(update, (image, i))
            self.db.commit()
            if self.debug:
                select = 'SELECT image FROM ' + self.DBtable + ' WHERE id = ? ;'
                print(select)
                self.c.execute(select, (i, ))
                testimage = self.c.fetchone()[0]
                test_out = '/home/jim/tools/TVSlideShow/imbedImage/test.jpg'
                with open(test_out, 'wb') as test_file:
                    size = test_file.write(testimage)
                doCmd('display ' + test_out)


def doCmd(command):
    #print('doCmd:', command)
    result = subprocess.run(command, shell = True, stdout = subprocess.PIPE, stderr=subprocess.STDOUT)
    #print(result.returncode, ':', result.stdout.decode('utf-8'))
    return result.returncode

def doCmdRetry(command, trys = 5, delay = 7):
    for attempt in range(trys):
        rc = doCmd(command)
        if rc == 0:
            return
        else:
            print('try:', attempt, ' rc:', rc, ' - ', command)
            time.sleep(delay)
    
def main():
    pictures = Pictures()
    pictures.getPictureFiles()

    '''
    images = Images()
    #images.addImages(5)
    images.addImages()
    '''
    
if __name__ == '__main__':
    # want unbuffered stdout for use with "tee"
    buffered = os.getenv('PYTHONUNBUFFERED')
    if buffered is None:
        myenv = os.environ.copy()
        myenv['PYTHONUNBUFFERED'] = 'Please'
        os.execve(sys.argv[0], sys.argv, myenv)
    main()
