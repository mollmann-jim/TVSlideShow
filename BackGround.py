#!/usr/bin/python3 -u


# Jim Mollmann
import datetime
import time
import math
import sys
import getopt
import os
import subprocess
import string
import sched
import random
import argparse
import sqlite3
import io
import struct
import pprint

class Picture:
    # select and get an image
    def __init__(self):
        self.directory = '/home/jim/bin/Slides/'
        self.srcIP     = '192.168.123.4'
        self.DB        = '/home/jim/tools/TVSlideShow.py/TVSlides.sql'
        self.DBtable   = 'pictures'
        self.DBmtime   = {'sql.new' : 0, 'sql.old' : 0, 'sql' : 0}
        self.myDBmtime = 0
        self.GetDB()
        self.myDBmtime = self.DBmtime['sql']
        self.db        = sqlite3.connect(self.DB)
        self.c         = self.db.cursor()
        countrows      = 'SELECT COUNT(*) FROM ' + self.DBtable + ';'
        self.c.execute(countrows)
        self.Rows      = self.c.fetchone()[0]
        print('rows:', self.Rows)
        #self.rowsleft  = list(range(1, self.Rows))
        self.n         = 0
        self.groupSize = 10
        self.group     = []
        self.rows      = {}
        self.files     = {}
        self.totalDirs = 0
        self.debug     = False

    def GetDB(self):
        # just restart if the database is newer
        pass
        '''
        restart = False
        debug = False
        DBbase = '.'.join(self.DB.split('.')[0 : -1]) + '.'
        for suffix in self.DBmtime.keys():
            db = DBbase + suffix
            if os.path.exists(db):
                self.DBmtime[suffix] = os.path.getmtime(db)
            else:
                self.DBmtime[suffix] = 0
            if debug: print(DBbase + suffix, ':', self.DBmtime[suffix])
        curDB = DBbase + 'sql'
        oldDB = curDB + '.old'
        newDB = curDB + '.new'
        if self.myDBmtime and self.DBmtime['sql'] > self.myDBmtime:
            print('DB updated:', curDB)
            restart = True
        elif self.DBmtime['sql.new'] > self.DBmtime['sql']:
            print(newDB, ' is newer than ', curDB)
            restart = True
            if os.path.exists(oldDB):
                command = 'rm ' + oldDB
                command = 'mv ' + oldDB + '.gone'
                doCmd(command, debug)
            command = ' '.join(['mv', curDB, oldDB])
            doCmd(command, debug)
            command = ' '.join(['mv', newDB, curDB])
            doCmd(command, debug)
        else:
            pass
        with open('/proc/' + str(os.getpid()) + '/cmdline', 'r') as cmdline:
            myCmd = cmdline.read()
        if restart:
            args = myCmd[0:-1].split('\0')
            path = args.pop(0)
            py = os.path.abspath(__file__)
            print('DB updated, restarting')
            os.execv(py, args)
        '''

    def getRange(self, idx, length):
        if length < self.groupSize:
            return 0, length - 1
        around = int(self.groupSize / 2)
        first = idx - around
        last  = idx + around
        if first < 0:
            last  = last - first
            first = 0
        if last > length - 1:
            first = first - (last - length)
            last  = length
        if self.debug:
            print('getRange: idx:', idx, 'length:', length, \
                  'first:', first, 'last:', last)
        return first, last

    def Get1Picture(self, workspace):
        self.n += 1
        # list idicies
        ROWNUM   = 0
        DIRFILE  = 1
        DIRNUM   = 0
        FILENUM  = 1

        if len(self.rows) == 0:
            # build "DB" of pictures
            select = 'SELECT dirNum, fileNum, filename FROM ' + \
                self.DBtable + ';'
            self.c.execute(select)
            rowNum = 0
            for row in self.c:
                dirNum, fileNum, filename = row
                self.rows[rowNum] = [dirNum, fileNum]
                if dirNum not in self.files:
                    self.files[dirNum] = {}
                self.files[dirNum][fileNum] = {'rowNum' : rowNum, 'filename' : filename}
                rowNum += 1
            self.totalDirs = len(self.files)

        if len(self.group) == 0:
            #check for a new DB
            self.GetDB()
            # need a new group of pictures to show
            selection = random.randint(0, len(self.rows) - 1)
            # sel = [ rowNum, [ dirNum, fileNum ] ]
            sel = list(sorted(self.rows.items()))[selection]
            if self.debug:
                print('sel:', sel)
            rowNum  = sel[ROWNUM]
            dirNum  = sel[DIRFILE][DIRNUM]
            fileNum = sel[DIRFILE][FILENUM]
            if self.debug:
                print(selection, rowNum, dirNum, fileNum)
            i = 0
            for fileNo in self.files[dirNum]:
                if fileNo == self.rows[rowNum][FILENUM]:
                    myIdx = i
                    break
                i += 1
            myDirLen = len(self.files[self.rows[rowNum][DIRNUM]])
            first, last = self.getRange(myIdx, myDirLen)
            i = 0
            deletes = []
            for fileNo in self.files[dirNum]:
                if i >= first and i <= last:
                    self.group.append(self.files[dirNum][fileNo]['filename'])
                    rowNum = self.files[dirNum][fileNo]['rowNum']
                    deletes.append([rowNum, dirNum, fileNo])
                i += 1
            if self.debug:
                print('deletes:', deletes)
            for rowNum, dirNum, fileNum in deletes:
                del self.files[dirNum][fileNum]
                if len(self.files[dirNum]) == 0:
                    del self.files[dirNum]
                del self.rows[rowNum]
            if self.debug:
                print('group:', self.group)

        filename = self.group.pop(0)
        select = 'SELECT rotate, label FROM ' + self.DBtable + ' WHERE filename = ? ;'
        self.c.execute(select, (filename,))
        (rotate, label) = self.c.fetchone()
        when = datetime.datetime.now().replace(microsecond = 0)
        print(f'{str(when):^19s}: {self.n:6d} - {workspace:2d} - {filename:s}')
        self.showStats(when)
        return (filename, rotate, label)

    def showStats(self, when):
        if when.minute > 0:
            return
        picsLeft = 0
        for dir in self.files:
            picsLeft += len(self.files[dir])
        picsLeft += len(self.group)
        print(f'{str(when):^19s}: {picsLeft:6d} of {self.Rows:6d} pictures remain')
        print(f'{" ":^19s}: {len(self.files):6d} of {self.totalDirs:6d} directories remain')


class Slide:
    # build & display image for screen
    # new image every 5 minutes, if needed
    def __init__(self, workspace):
        #self.resolution = "1920x1080"
        self.pictures    = Picture()
        #self.VolumeUp   = True
        self.imageDir    = '/home/jim/tools/TVSlideShow.py/images/'
        self.picRoot     = '/home/jim/pictures/'
        self.workspace   = workspace
        self.idx         = 0
        self.debug       = False

    def Show1Slide(self):
        workDir = '/tmp/'
        (filename, rotate, label) = self.pictures.Get1Picture(self.workspace)
        ext = filename.split('.')[-1].lower()
        isPEF =  ext == 'pef'
        isTIF =  ext == 'tif'
        isHDR = 'HDR' in label
        imageNum = PEF = strip = ''
        if isTIF:
            imageNum = '[0]'
        if isPEF:
            PEF = 'PEF:'
        if isHDR:
            strip = ' -strip '
        self.idx += 1
        idx = self.idx % 5
        wksp = f'{self.workspace:d}'
        try:
            with open(self.picRoot + filename, 'rb') as image_file:
                orgImage = image_file.read()
        except Exception as e:
            print('ABORT: Failed initial read', filename, e)
        #print('Show1Slide', filename)
        if orgImage is None:
            print('orgImage is "None". Skipping.')
            return
        
        resize = ' -resize 3640x2088 '
        cmd = 'magick ' + PEF + '- -auto-orient ' + rotate + resize  + \
            strip + ' -quality 95 jpeg:-'
        result = doCmd(cmd, debug = False, input = orgImage)
        if result.returncode != 0:
            print('ERROR: Show1Slide: initial image:', filename)
            result.stdout = orgImage
        resizeImage = result.stdout
        
        try:
            width, height = self.get_jpeg_dimensions_from_bytes(resizeImage)
        except ValueError:
            print('ERROR: addPicture: get_jpeg_dimensions_from_bytes:', filename)
            width, height = 3440, 2160
            
        labelText  = f'{workDir:s}label{idx:d}{wksp:s}.txt'
        with open(labelText, 'w') as Label:
            Label.write(label + '\n')

        if width <= 3440:
            cmd = 'magick -  \\( -background "black" '     \
                ' -fill "white" -font "NimbusSans-Bold" -pointsize 14 ' \
                ' -interline-spacing 6 -size 200x -gravity NorthWest  ' \
                ' caption:@' + labelText + ' \\) +append -'
            result = doCmd(cmd, input = resizeImage)
            if result.returncode != 0:
                print('ERROR: Show1Slide: final image:', filename)
                result.stdout = resizeImage
        else:
            cmd = 'magick - -font NimbusSans-Bold -pointsize 20 -fill red' \
                ' -stroke black -strokewidth 1 -gravity NorthEast '\
                ' -annotate +0+0 @' + labelText + ' - '
            result = doCmd(cmd, input = resizeImage)
            if result.returncode != 0:
                print('ERROR: addPicture: final annotated image:', filename)
                result.stdout = resizeImage
        image = result.stdout
        
        displayFile = self.imageDir + 'display.' + str(idx) + wksp +'.jpg'
        
        with open(displayFile, 'wb') as display_file:
            size = display_file.write(image)
        #
	# run "xfconf-query -c xfce4-desktop -m" from the CLI
	# use the GUI to change the desktop background and note the name
	# turn off "apply to all workspaces
	#
        if self.debug:
            command = 'display ' + displayFile
        else:
            command = 'xfconf-query -c xfce4-desktop ' +            \
                '-p /backdrop/screen0/monitorHDMI-0/workspace' + wksp + \
                '/last-image -s ' + displayFile
        #print(command)
        doCmd(command)
        
    def get_jpeg_dimensions_from_bytes(self, jpeg_bytes: bytes):
        # Parse a JPEG byte string to determine the pixel dimensions (width, height).
        # From Google AI
        stream = io.BytesIO(jpeg_bytes)
        # 1. Verify JPEG SOI (Start of Image) marker: \xff\xd8
        if stream.read(2) != b'\xff\xd8':
            stream.seek(0)
            print('get_jpeg_dimensions_from_bytes:', stream.read(2))
            raise ValueError("Not a valid JPEG file.")
        while True:
            # 2. Read the segment marker (usually \xff followed by a marker byte)
            marker = stream.read(2)
            if not marker or marker[0] != 0xff:
                break
            marker_type = marker[1]
            # 3. Check for Start of Frame (SOF) markers (SOF0 to SOF2)
            if 0xc0 <= marker_type <= 0xc2:
                # Skip segment length (2 bytes) and precision (1 byte)
                stream.read(3)
                # Read Height and Width (2 bytes each, big-endian unsigned short)
                height, width = struct.unpack('>HH', stream.read(4))
                return width, height
            # 4. Skip over non-SOF segments by reading their length
            else:
                length_bytes = stream.read(2)
                if not length_bytes:
                    break
                segment_length = struct.unpack('>H', length_bytes)[0]
                stream.seek(segment_length - 2, io.SEEK_CUR)

class SlideTimer:
    # handle when to display a picture
    def __init__(self, scheduler, workspace):
        self.showSlide = True
        self.scheduler = scheduler
        self.frequency = 5 * 60
        self.starttime = 0
        self.slides    = Slide(workspace)
        self.workspace = workspace

    def Schedule(self, frequency = None):
        if frequency:
            self.frequency = frequency
        now = datetime.datetime.now()
        firstTime = now.replace(hour = 0, minute = 0, second = 0, microsecond = 0) -\
                    datetime.timedelta(weeks = 1)
        while firstTime < now:
            firstTime += datetime.timedelta(seconds = self.frequency)
        self.starttime = firstTime
        print('showSlide Start time:', self.starttime, 'workspace:',self.workspace)
        self.scheduler.enterabs(time.mktime(self.starttime.timetuple()), 1,
                                self.ShowSlide,
                                kwargs = {'WKSP': self.workspace})

    def ShowSlide(self, WKSP = None):
        self.starttime = self.starttime + datetime.timedelta(seconds = self.frequency)
        self.scheduler.enterabs(time.mktime(self.starttime.timetuple()), 1,
                                self.ShowSlide,
                                kwargs = {'WKSP': self.workspace})
        self.slides.Show1Slide()
        
def doCmd(command, printFailure = True, debug = False, input = None):
    if debug:
        print('doCmd:command:', command)
    result = subprocess.run(command, shell = True, stdout = subprocess.PIPE, \
                            stderr=subprocess.PIPE, input = input, check = False)
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

def main():
    scheduler = sched.scheduler(time.time, time.sleep)
    #power = Power(scheduler)
    for workspace in range(7,9):
        slides = SlideTimer(scheduler, workspace)
        slides.Schedule(frequency = 1 * 60)
    #power.Schedule()

    print(len(scheduler.queue))
    #print(scheduler.queue)
    for event in scheduler.queue:
        print('Next:', datetime.datetime.fromtimestamp(event.time).replace(microsecond = 0),
              'Action:', str(event.action).split(' ')[2],
              'Pri:', event.priority,
              'Arg:', event.argument,
              'WKSP:', event.kwargs['WKSP'])

    scheduler.run()

if __name__ == '__main__':
  main()
