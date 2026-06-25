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
import pprint
from fractions import Fraction

def adapt_datetime(dt):
    return dt.isoformat(sep=' ').replace('T', ' ')

def convert_datetime(val):
    return dt.datetime.fromisoformat(val)

class Pictures:
    def __init__(self):
        self.picRoot       = '/home/jim/pictures/'
        self.rotates       = {}
        self.filesInDir    = {}

    def getPictureFiles(self):
        imageExt = ['*jpg', '*.jpeg', '*pef', '*tif', '*gif',
                    '*JPG', '*.JPEG', '*PEF', '*TIF', '*GIF']
        unwantedDirs = ['xvpics', 'allergy', '4sale', 'small', 'images',
                        'Jaye', 'test', 'Test2', 'Rotate', 'cull']
        picDirLen = len(self.picRoot)
        picturesDir = Path(self.picRoot)
        image_paths = itertools.chain.from_iterable(picturesDir.rglob(ext) for ext in imageExt)
        for picture in image_paths:
            directory = str(picture.parent)[picDirLen:] + '/'
            if directory not in self.filesInDir:
                self.filesInDir[directory] = []
            self.filesInDir[directory].append(str(picture.name))
        for dir in sorted(self.filesInDir):
            for remove in unwantedDirs:
                if remove in dir:
                    del self.filesInDir[dir]
                    break
        subDirs = []
        for dir1 in sorted(self.filesInDir):
            if dir1 in subDirs:
                continue
            subDirDict = {k : v for k, v in self.filesInDir.items() if k.startswith(dir1)}
            for dir2 in sorted(subDirDict):
                if dir1 == dir2:
                    continue
                subDirs.append(dir2)
        for dir in subDirs:
            del self.filesInDir[dir]
            
        return self.filesInDir

    def getRotate(self, filename):
        if len(self.rotates) == 0:
            self.buildRotates()
            self.flopSlides()
        basename = filename.split('/')[-1]
        if self.rotates.get(basename, False):
            print('rotate', basename, filename, self.rotates[basename])
            return self.rotates[basename]
        else:
            return ''

    def buildRotates(self):
        dirs         = ['FlipLR', 'FlipUD', 'L90', 'R180', 'R90']
        rotateOpts   = [' -flip ', ' -rotate 180 ', ' -rotate -90 ',
                        ' -rotate 180 ', ' -rotate 90 ']
        for subDir, option in zip(dirs, rotateOpts):
            self.getRotates(subDir, option)

    def getRotates(self, subDir, option):
        rotateBase = self.picRoot + 'Rotate/' + subDir
        rotPath = Path(rotateBase)
        for rot in rotPath.rglob('*'):
            file = str(rot.name)
            self.rotates[file] = option

    def flopSlides(self):
        slideDirDict = {k : v for k, v in self.filesInDir.items() if k.startswith('Slides')}
        for slideDir in slideDirDict:
            for file in slideDirDict[slideDir]:
                self.rotates[slideDir + file] = ' -flop '
        
    def countLabels(self):
        fields = {}
        for dir in sorted(self.filesInDir):
            for file in self.filesInDir[dir]:
                labelData = self.getLabelData(dir + file)
                for meta in labelData:
                    fields[meta] = 1 + fields.get(meta, 0)
        for meta in sorted(fields):
            print(f'{fields[meta]:6d} : {meta:s}')
        return
                    
    def buildLabels(self, filesInDir):
        labels = {}
        for dir in sorted(self.filesInDir):
            for file in self.filesInDir[dir]:
                labelData = self.getLabelData(dir + file)
                labels[dir + file] = self.composeLabel(dir + file, labelData)

    def getLabel(self, file):
        meta = self.getLabelData(file)
        label = self.composeLabel(file, meta)
        return label

    def getLabelData(self, file):
        self.pp = pprint.PrettyPrinter(indent=4, sort_dicts=False)
        cmd = 'identify -verbose "' + self.picRoot + file + '"'
        result = doCmd(cmd)
        kv_regex = re.compile(r"^\s+([\w\s]+):\s*(.*)$")
        metadata = {}
        for line in result.stdout.splitlines():
            line = line.decode('utf-8').replace('date:', '')
            line = line.replace('exif:', '').replace('jpeg:', '')
            match = kv_regex.match(line)
            if match:
                # clean up keys and store values
                key = match.group(1).strip().lower().replace(" ", "_")
                value = match.group(2).strip()
                metadata[key] = value
        return metadata

    def composeLabel(self, filename, metadata):
        label = '\n\n\n\n\n\n\n'
        label += filename.replace('/', '\n') +'\n\n\n'
        birthday = time = None
        if metadata.get('datetime', False):
            time     = metadata['datetime']
            birthday = dt.datetime.strptime(time, '%Y:%m:%d %H:%M:%S')
        elif metadata.get('modify', False):
            time     = metadata['modify']
            birthday = dt.datetime.strptime(time, '%Y-%m-%dT%H:%M:%S+00:00')
        elif metadata.get('createdate', False):
            time     = metadata['createdate']
            birthday = 'createdate' + metadata['createdate']
        elif metadata.get('filemodifydate', False):
            time     = metadata['filemodifydate']
            birthday = 'filemodifydate' + metadata['filemodifydate']
        else:
            print(filename, 'needs birthday')
            pprint.pprint(metadata)
        if time is not None:
            label += time + '\n\n'

        if metadata.get('shutterspeedvalue', False):
            ss = float(Fraction(metadata['shutterspeedvalue']))
            label += f'ShutterSpeed: {ss:7.4f}\n'
        if metadata.get('photographicsensitivity', False):
            label += 'ISO: ' + metadata['photographicsensitivity'] + '\n'
        if metadata.get('focallength', False):
            fl = float(Fraction(metadata['focallength']))
            label += f'FocalLength: {fl:6.1f}\n'
        if metadata.get('focallengthin35mmfilm', False):
            fl = float(Fraction(metadata['focallengthin35mmfilm']))
            label += f'FocalLength)35mm): {fl:6.1f}\n'
        if metadata.get('fnumber', False):
            ap = float(Fraction(metadata['fnumber']))
            label += f'Aperture: {ap:6.1f}\n'
        if metadata.get('exposuretime', False):
            label += f'Exposure: {metadata['exposuretime']:s}s\n'
        if metadata.get('make', False):
            label += f'Make: {metadata['make']:s}\n'
        if metadata.get('lensmodel', False):
            label += f'Lens: {metadata['lensmodel']:s}\n'
        if metadata.get('gpslatitude', False):
            lat = [deg, min, sec] = metadata['gpslatitude'].split(',')
            for i in range(len(lat)):
                lat[i] = float(Fraction(lat[i]))
            ref = metadata.get('gpslatituderef', '')
            label += f'Latitude:  {lat[0]:4.0f} {lat[1]:3.0f}\' {lat[2]:4.1f}" {ref:s}\n'
        if metadata.get('gpslongitude', False):
            long = [deg, min, sec] = metadata['gpslongitude'].split(',')
            for i in range(len(long)):
                long[i] = float(Fraction(long[i]))
            ref = metadata.get('gpslongituderef', '')
            label += f'Longitude: {long[0]:4.0f} {long[1]:3.0f}\' {long[2]:4.1f}" {ref:s}\n'
        if metadata.get('gpsaltitude', False):
            alt = float(Fraction(metadata['gpsaltitude']))
            label += f'Altitude: {alt:5.1f} m   {alt * 3.28084:5.1f} \'\n'
        if metadata.get('gpsimgdirection', False):
            dir = float(Fraction(metadata['gpsimgdirection']))
            label += f'Image Direction: {dir:4.0f} deg\n'
        if metadata.get('gpsdestbearinggpsimg', False):
            dir = float(Fraction(metadata['gpsdestbearing']))
            label += f'Bearing: {dir:4.0f} deg\n'
        if metadata.get('gpsspeed', False):
            spd = float(Fraction(metadata['gpsspeed']))
            label += f'Speed {spd:4.0f} m/s  {spd:4.0f} mph\n'    
        return label, birthday

class buildImageDB:
    def __init__(self):
        self.picRoot = '/home/jim/pictures/'
        self.DB = '/home/jim/tools/TVSlideShow.py/TVSlides.sql'
        self.DBtable = 'pictures'
        sqlite3.register_adapter(dt.datetime, adapt_datetime)
        sqlite3.register_converter("DATETIME", convert_datetime)
        self.db = sqlite3.connect(self.DB, detect_types=sqlite3.PARSE_DECLTYPES)
        self.c = self.db.cursor()
        self.initDB()

    def initDB(self):
        create = 'CREATE TABLE IF NOT EXISTS ' + self.DBtable + ' ( \n' +\
            'filename       TEXT PRIMARY KEY,                       \n' +\
            'timestamp      INTEGER DEFAULT CURRENT_TIMESTAMP,      \n' +\
            'rotate         TEXT DEFAULT NULL,                      \n' +\
            'inode          INTEGER,                                \n' +\
            'md5sum         TEXT,                                   \n' +\
            'birthday       INTEGER,                                \n' +\
            'image          BLOB DEFAULT NULL                       \n' +\
            ');'
        self.c.execute(create)


class Images:
    def __init__(self):
        self.directory = '/home/jim/tools/TVSlideShow.py/'
        #self.DBx = '/home/jim/tools/TVSlideShow.py/makeDB/TVslides.image.test.sql'
        self.DB = '/home/jim/tools/TVSlideShow.py/sql/TVslides.sql'
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

        
def doCmd(command, printFailure = True, debug = False):
    if debug:
        print('doCmd:command:', command)
    result = subprocess.run(command, shell = True, stdout = subprocess.PIPE, \
                            stderr=subprocess.STDOUT, check = False)
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
                  

def doCmdOrg(command):
    #print('doCmd:', command)
    result = subprocess.run(command, shell = True, stdout = subprocess.PIPE,
                            stderr=subprocess.STDOUT, check = False)
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
    picList  = pictures.getPictureFiles()
    #rotates  = pictures.buildRotates()
    #rotates  = pictures.flopSlides(picList)
    '''
    #pictures.countLabels(picList)
    #pprint.pprint(rotates)
    
    '''
    rotate = pictures.getRotate('/home/jim/pictures/Rotate/R90/2004.Athens-Barcelona_Florence.Livorno.Italy_PA310134.jpg')

    z= rotate / 0

    build    = buildImageDB()
    i = -1
    skip = 999999
    skip = 1
    for dir in sorted(picList):
        for file in sorted(picList[dir]):
            i += 1
            if i % skip != 0:
                continue
            filename = dir + file
            #print(f'{i:6d} : {filename:s}')
            #### label, bday = pictures.getLabel(filename)
            rotate = pictures.getRotate(filename)
            #print(bday)
            #print(label)

    

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
