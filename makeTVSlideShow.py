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
import hashlib
import random
from contextlib import suppress

def adapt_datetime(dt):
    return dt.isoformat(sep=' ').replace('T', ' ')

def convert_datetime(val):
    return dt.datetime.fromisoformat(val)

class Pictures:
    def __init__(self, pictureRoot, debug):
        self.debug           = debug
        self.debugRotateMsgs = False
        self.picRoot         = pictureRoot
        self.rotates         = {}
        self.filesInDir      = {}
        self.debugRotates    = {}
        self.dbgRotatesCpy   = {}
        self.unwantedDirs = ['xvpics', 'allergy', '4sale', 'small', 'images',
                             'Jaye', 'test', 'Test2', 'Rotate', 'cull', 'unknown']

    def getPictureFiles(self):
        imageExt = ['*jpg', '*jpeg', '*pef', '*tif', '*gif', '*bmp', '*png', '*heic',
                    '*JPG', '*JPEG', '*PEF', '*TIF', '*GIF', '*BMP', '*PNG', '*HEIC']
        picDirLen = len(self.picRoot)
        picturesDir = Path(self.picRoot)
        image_paths = itertools.chain.from_iterable(picturesDir.rglob(ext) \
                                                    for ext in imageExt)
        for picture in image_paths:
            directory = str(picture.parent)[picDirLen:] + '/'
            if directory not in self.filesInDir:
                self.filesInDir[directory] = []
            self.filesInDir[directory].append(str(picture.name))
        if self.debug:
            dirs, files = self.countFiles()
            print('getPictureFiles:', dirs, ' directories',
                  files, ' files in filesInDir after initial scan')

        for dir in sorted(self.filesInDir):
            for remove in self.unwantedDirs:
                if remove in dir:
                    del self.filesInDir[dir]
                    break
        if self.debug:
            dirs, files = self.countFiles()
            print('getPictureFiles:', dirs, ' directories',
                  files, ' in filesInDir after remove unwanted')
        subDirs = []
        for dir1 in sorted(self.filesInDir):
            if dir1 in subDirs:
                continue
            subDirDict = {k : v for k, v in self.filesInDir.items() \
                          if k.startswith(dir1)}
            for dir2 in sorted(subDirDict):
                if dir1 == dir2:
                    continue
                subDirs.append(dir2)
        for dir in subDirs:
            del self.filesInDir[dir]
        self.cullFiles()
        if self.debug:
            dirs, files = self.countFiles()
            print('getPictureFiles:', dirs, ' directories',
                  files, ' files in filesInDir at end')
        return self.filesInDir

    def countFiles(self):
        if self.debug:
            cnt = 0
            for dir in self.filesInDir:
                cnt += len(self.filesInDir[dir])
            return len(self.filesInDir), cnt
        return 0, n

    def cullFiles(self):
        culls = {}
        self.getRotates('Cull', 'cull', culls)
        #pprint.pprint(culls)
        for cull in culls:
            cullPath = Path(cull)
            cullDir  = str(cullPath.parent) + '/'
            cullFile = str(cullPath.name)
            if self.filesInDir.get(cullDir, False):
                if cullFile in self.filesInDir[cullDir]:
                    self.filesInDir[cullDir].remove(cullFile)
                else:
                    print(cullFile, ' not in ', cullDir)
            else:
                print(cullDir + cullFile,
                      ' directory not found in self.filesInDir')

    def setupDebugRotate(self):
        if  self.debugRotateMsgs:
            print('self.rotates:start:', len(self.rotates),
                  'self.dbgRotatesCpy:', len(self.dbgRotatesCpy))
        self.dbgRotatesCpy = self.rotates.copy()
        for subDir, option in zip(['Cull', 'OK'], ['Cull', 'OK']):
            self.getRotates(subDir, option, self.dbgRotatesCpy)
        for fullname in self.dbgRotatesCpy:
            filename = fullname.split('/')[-1].lower()
            if filename not in self.debugRotates:
                self.debugRotates[filename] = []
            self.debugRotates[filename].append(fullname)

    def debugRotate(self, fullname):
        filename = fullname.split('/')[-1].lower()
        if self.debugRotates.get(filename, False):
            for rot in self.debugRotates[filename]:
                if rot == fullname:
                    if self.debugRotateMsgs:
                        print('debugRotate: match:', rot,
                              self.dbgRotatesCpy[fullname])
                elif self.dbgRotatesCpy[rot] == 'OK':
                    if self.debugRotateMsgs:
                        print('debugRotate:', fullname,
                              ' possible match:', rot,
                              self.dbgRotatesCpy[rot])
                else:
                    print('debugRotate:', fullname,
                          ' possible match:', rot,
                          self.dbgRotatesCpy[rot])
        else:
            if self.debugRotateMsgs:
                print('debugRotate: no possible rotates:', fullname)

    def getRotate(self, filename):
        if len(self.rotates) == 0:
            self.buildRotates()
            self.flopSlides()
            self.setupDebugRotate()
        if self.rotates.get(filename, False):
            #print('rotate', filename, self.rotates[filename])
            return self.rotates[filename]
        else:
            self.debugRotate(filename)
            return ''

    def buildRotates(self):
        dirs         = ['FlipLR', 'FlipUD', 'L90', 'R180', 'R90']
        rotateOpts   = [' -flip ', ' -rotate 180 ', ' -rotate -90 ',
                        ' -rotate 180 ', ' -rotate 90 ']
        for subDir, option in zip(dirs, rotateOpts):
            self.getRotates(subDir, option, self.rotates)
            print('buildRotates:', subDir, len(self.rotates))

    def getRotates(self, subDir, option, rotatesDict):
        rotateBase = self.picRoot + 'Rotate/' + subDir
        rotPath = Path(rotateBase)
        i = 0
        for rot in rotPath.rglob('*'):
            file = str(rot.name).replace('_', '/')
            if not any( dir in file for dir in self.unwantedDirs):
                rotatesDict[file] = option
                i += 1
        print('getRotates:', subDir, ' - ', i, len(rotatesDict))

    def flopSlides(self):
        slideDirDict = {k : v for k, v in self.filesInDir.items() if k.startswith('Slides')}
        i = 0
        for slideDir in slideDirDict:
            for file in slideDirDict[slideDir]:
                self.rotates[slideDir + file] = ' -flop '
                i += 1
        print('flopSlides:', i, len(self.rotates))

    def countLabels(self):
        fields = {}
        for dir in sorted(self.filesInDir):
            for file in self.filesInDir[dir]:
                labelData = self.getLabelData(dir + file, None)
                print('\n' + dir + file)
                pprint.pprint(labelData)
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
                
    def getLabel(self, filename, orgImage):
        #meta = self.getLabelData(filename)
        #print('getLabel:', filename, len(orgImage), type(orgImage))
        meta = self.getLabelData(filename, orgImage)
        label = self.composeLabel(filename, meta)
        return label

    def getLabelData(self, filename, orgImage):
        self.pp = pprint.PrettyPrinter(indent=4, sort_dicts=False)
        ext = filename.split('.')[-1].lower()
        isPEF =  ext == 'pef'
        if orgImage is None or isPEF:
            cmd = 'magick identify -verbose "' + self.picRoot + filename + '"'
            result = doCmd(cmd)
        elif isPEF:
            cmd = 'magick identify -verbose PEF:-'
            result = doCmd(cmd, input = orgImage)
        else:
            cmd = 'magick identify -verbose -'
            #print('getLabelData:', cmd)
            result = doCmd(cmd, input = orgImage)
        kv_regex = re.compile(r"^\s+([\w\s]+):\s*(.*)$")
        metadata = {}
        for line in result.stdout.splitlines():
            try:
                line = line.decode('utf-8').replace('date:', '').replace('dng:', '')
                line = line.replace('exif:', '').replace('jpeg:', '')
            except Exception as e:
                lineHex = line.hex(' ', bytes_per_sep = -4)
                print(f'Skipping file {filename:s}')
                print(f'line(hex): {lineHex:s}')
                print(f' due to error: {e}')
                for word in lineHex.split():
                    char = bytes.fromhex(word)
                    print(word, ' : ', char)
                continue
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
            with suppress(ValueError):
                birthday = dt.datetime.strptime(time, '%Y:%m:%d %H:%M:%S')
        if birthday is None and  metadata.get('modify', False):
            time     = metadata['modify']
            with suppress(ValueError):
                birthday = dt.datetime.strptime(time, '%Y-%m-%dT%H:%M:%S+00:00')
        if birthday is None and metadata.get('filemodifydate', False):
            time     = metadata['filemodifydate']
            with suppress(ValueError):
                birthday = 'filemodifydate' + metadata['filemodifydate']
        if birthday is None and metadata.get('create', False): 
            time     = metadata['create']
            with suppress(ValueError):
                birthday = dt.datetime.strptime(time, '%Y-%m-%dT%H:%M:%S+00:00')
        if birthday is None and metadata.get('create.date', False): 
            time     = metadata['create.date']
            with suppress(ValueError):
                birthday = dt.datetime.strptime(time, '%Y-%m-%dT%H:%M:%S+00:00')
        if birthday is None:
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
        if metadata.get('orientation', False):
            orient = metadata['orientation']
            rotate = self.getRotate(filename)
            if rotate == 'flop' or rotate == '':
                pass
            elif rotate != '' and (orient == 'TopLeft' or orient == 'Undefined'):
                print('Rotate only orientation:', orient, 'rotate:', rotate, filename)
            elif (rotate == 'R180' and orient == 'BottomRight') or \
                 (rotate == 'R90'  and orient == 'LeftBottom' ) or \
                 (rotate == 'L90'  and orient == 'RightTop'):
                print('Double fixup orientation:', orient, 'rotate:', rotate, filename)
            else:
                print('Conflicting fixup orientation:', orient, 'rotate:', rotate, filename)
        return label, birthday

class buildImageDB:
    def __init__(self, pictureRoot, debug):
        self.debug   = debug
        self.picRoot = '/home/jim/pictures/'
        self.DB      = '/home/jim/tools/TVSlideShow.py/TVSlides.sql'
        self.DBtable = 'pictures'
        sqlite3.register_adapter(dt.datetime, adapt_datetime)
        sqlite3.register_converter("DATETIME", convert_datetime)
        self.db = sqlite3.connect(self.DB, detect_types=sqlite3.PARSE_DECLTYPES)
        self.c = self.db.cursor()
        self.initDB()

    def initDB(self):
        if self.debug:
            drop = 'DROP TABLE IF EXISTS ' + self.DBtable + ';'
            self.c.execute(drop)
        create = 'CREATE TABLE IF NOT EXISTS ' + self.DBtable + ' (  \n' +\
            ' filename       TEXT PRIMARY KEY,                       \n' +\
            ' timestamp      INTEGER DEFAULT CURRENT_TIMESTAMP,      \n' +\
            ' rotate         TEXT DEFAULT NULL,                      \n' +\
            ' inode          INTEGER,                                \n' +\
            ' md5sum         TEXT,                                   \n' +\
            ' birthday       INTEGER,                                \n' +\
            ' filesize       INTEGER,                                \n' +\
            ' label          TEXT,                                   \n' +\
            ' dirNum         INTEGER,                                \n' +\
            ' fileNum        INTEGER,                                \n' +\
            ' image          BLOB DEFAULT NULL                       \n' +\
            ' );'
        self.c.execute(create)

    def addPicture(self, filename, rotate, label, bday, orgImage, dirNum, fileNum):
        workDir = '/tmp/'
        #workDir = '/home/jim/tools/TVSlideShow.py/test.out/'
        insert = 'INSERT OR REPLACE INTO ' + self.DBtable + ' ( \n'    \
            ' filename, rotate, inode, md5sum, birthday, filesize, \n' \
            ' label, dirNum, fileNum, image) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?);'
        fullname = self.picRoot + filename
        stat = os.stat(fullname)
        md5sum = hashlib.md5(orgImage).hexdigest()

        print('addPicture:', filename, rotate, bday, stat.st_ino,
              stat.st_size, md5sum, rotate)
        values = [filename, rotate, stat.st_ino, md5sum, bday,
                  stat.st_size, label, dirNum, fileNum, None]
        self.c.execute(insert, values)
        self.db.commit()

        tgtFile  = workDir + 'slideOut.jpg'
        tgtFile2  = workDir + 'slideOut-0.jpg'
        ext = filename.split('.')[-1].lower()
        isPEF =  ext == 'pef'
        # -auto-orient and/or rotate???
        if fullname.split('.')[-1] == 'tif':
            imageNum = '[0]'
        else:
            imageNum = ''
        if isPEF:
            cmd = 'magick PEF:- -auto-orient ' + rotate + '-resize 1720x1080' + \
            ' -quality 95 jpeg:-'
        else:
            cmd = 'magick -' + imageNum + ' -auto-orient ' + rotate + '-resize 1720x1080' + \
                ' -quality 95 jpeg:-'
        result = doCmd(cmd, debug = False, input = orgImage)

        if result.returncode != 0:
            print('ABORT: addPicture: initial image:', filename)
            return False
        resizeImage = result.stdout
        #print('resizeImage:', len(resizeImage))
        
        labelText  = workDir + 'label.txt'
        labelImage = workDir + 'label.jpg'
        with open(labelText, 'w') as Label:
            Label.write(label + '\n')
        cmd = 'magick -size 200x1080 -background grey  -fill black  -font NimbusSans-Bold '\
            '-pointsize 11 label:@' + labelText + ' ' + labelImage
        result = doCmd(cmd, debug = False)
        if result.returncode != 0:
            print('ABORT: addPicture: label image:', filename)
            print('label:', label)
            return False
        slideFile = workDir + 'slide.jpg'

        #cmd = 'magick -background grey - ' + labelImage + ' +append ' + slideFile
        cmd = 'magick -background grey jpeg:- ' + labelImage + ' +append jpeg:-'
        result = doCmd(cmd, input = resizeImage)
        if result.returncode != 0:
            print('ABORT: addPicture: initial + label image:', filename)
            print(result.stderr)
            print('label:', label, len(resizeImage))
            return False
        labeledImage = result.stdout

        cmd = 'magick - -resize 1920x1080 -quality 95 jpeg:-'
        result = doCmd(cmd, input = labeledImage)
        if result.returncode != 0:
            print('ABORT: addPicture: final image:', filename)
            return False
        image = result.stdout

        update = 'UPDATE ' + self.DBtable + ' SET image = ? WHERE filename = ? ;'
        self.c.execute(update, [image, filename])
        self.db.commit()
        
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
    debug       = True
    pictureRoot = '/home/jim/pictures/'
    pictures = Pictures(pictureRoot, debug)
    #pictures.picRoot = '/home/jim/pictures/Edgecliff/Edgecliff friends/'
    picList  = pictures.getPictureFiles()
    #pictures.countLabelsNone)
    
    build    = buildImageDB(pictureRoot, debug)
    i = -1
    skip = 999999
    skip = 10000
    skip = 1
    dirNum = 0
    for dir in sorted(picList):
        dirNum += 1
        fileNum = 0
        for file in sorted(picList[dir]):
            fileNum +=1
            i += 1
            if i % skip != 0:
                continue
            filename = dir + file
            #print(f'{i:6d} : {filename:s}')
            '''
            ext = filename.split('/')[-1]
            if ext != 'IMGP1559.PEF':
                continue
            '''
            with open(pictureRoot + filename, 'rb') as image_file:
                orgImage = image_file.read()
            label, bday = pictures.getLabel(filename, orgImage)
            
            #label, bday = pictures.getLabel(filename)
            
            rotate = pictures.getRotate(filename)
            #continue
            build.addPicture(filename, rotate, label, bday, orgImage, dirNum, fileNum)
    
if __name__ == '__main__':
    # want unbuffered stdout for use with "tee"
    buffered = os.getenv('PYTHONUNBUFFERED')
    if buffered is None:
        myenv = os.environ.copy()
        myenv['PYTHONUNBUFFERED'] = 'Please'
        os.execve(sys.argv[0], sys.argv, myenv)
    main()
