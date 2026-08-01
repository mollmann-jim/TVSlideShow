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
        self.groupSize = 11
        self.group     = []
        self.rows      = {}
        self.files     = {}
        self.totalDirs = 0
        self.debug     = False

    def GetDB(self):
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

    def Get1Picture(self):
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
            self.totalDirs = rowNum - 1

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
                del self.rows[rowNum]
            if self.debug:
                print('group:', self.group)

        filename = self.group.pop(0)
        select = 'SELECT image FROM ' + self.DBtable + ' WHERE filename = ? ;'
        self.c.execute(select, (filename,))
        (image,) = self.c.fetchone()
        when = datetime.datetime.now().replace(microsecond = 0)
        print(f'{str(when):^19s}: {self.n:6d} {filename:s}')
        self.showStats(when)
        return (filename, image)

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
    def __init__(self,):
        #self.resolution = "1920x1080"
        self.pictures   = Picture()
        #self.VolumeUp   = True
        self.directory  = '/home/jim/tools/TVSlideShow.py/images/'
        self.idx        = 0
        self.debug      = False

    def Show1Slide(self):
        (filename, image) = self.pictures.Get1Picture()
        #print('Show1Slide', filename)
        if image is None:
            print('Image is "None". Skipping.')
            return
        self.idx += 1
        idx = self.idx % 20
        displayFile = self.directory + 'display.' + str(idx) + '.jpg'
        with open(displayFile, 'wb') as display_file:
            size = display_file.write(image)

        if self.debug:
            command = 'display ' + displayFile
        else:
            command = 'pkill -TERM fbi'
            doCmd(command)
            command = '/usr/bin/fbi -T 1 --noverbose ' + displayFile
        doCmd(command)

class SlideTimer:
    # handle when to display a picture
    def __init__(self, scheduler, power):
        self.showSlide = True
        self.scheduler = scheduler
        self.frequency = 5 * 60
        self.starttime = 0
        self.slides    = Slide()
        self.power     = power

    def Schedule(self, frequency = None):
        if frequency:
            self.frequency = frequency
        now = datetime.datetime.now()
        firstTime = now.replace(hour = 0, minute = 0, second = 0, microsecond = 0) -\
                    datetime.timedelta(weeks = 1)
        while firstTime < now:
            firstTime += datetime.timedelta(seconds = self.frequency)
        self.starttime = firstTime
        print('showSlide Start time:', self.starttime)
        self.scheduler.enterabs(time.mktime(self.starttime.timetuple()), 1, self.ShowSlide, ())

    def ShowSlide(self):
        self.starttime = self.starttime + datetime.timedelta(seconds = self.frequency)
        self.scheduler.enterabs(time.mktime(self.starttime.timetuple()), 1, self.ShowSlide, ())
        if Power.GetPower(self.power):
            Power.SetTVPower(self.power)
            self.slides.Show1Slide()


class Power:
    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.on = True
        self.morningOn =  ['05:30', '05:30', '05:30', '05:30', '05:30', '07:00', '07:00']
        self.morningOff = ['07:11', '07:11', '07:11', '07:11', '07:11', '23:27', '23:27']
        self.eveningOn =  ['16:00', '16:00', '16:00', '16:00', '16:00', None, None]
        self.eveningOff = ['22:22', '22:22', '22:22', '22:22', '23:22', None, None]

        self.morningOn =  ['06:00', '06:00', '06:00', '06:00', '06:00', '06:00', '06:00']
        self.morningOff = ['22:22', '22:22', '22:22', '22:22', '22:22', '23:27', '23:27']
        self.eveningOn =  ['01:01', '02:02', '03:03', '04:04', '03:33', '02:22', '01:11']
        self.eveningOff = ['02:02', '03:03', '04:04', '05:05', '04:44', '03:33', '02:22']

    def SetTVPower(self):
        if self.on:
            command = 'echo on 0 | cec-client -s -d 1'
        else:
            command = 'echo standby 0 | cec-client -s -d 1'
        doCmd(command)

    def GetPower(self):
        return self.on

    def SetPowerOn(self):
        self.on = True
        print('{0:^19s}: Power set on'.format(str(datetime.datetime.now().replace(microsecond = 0))))
        now = datetime.datetime.now()
        self.SetTVPower()
        nextTime = now.replace(second = 0) + datetime.timedelta(weeks = 1)
        self.scheduler.enterabs(time.mktime(nextTime.timetuple()), 1, self.SetPowerOn, ())

    def SetPowerOff(self):
        self.on = False
        print('{0:^19s}: Power set off'.format(str(datetime.datetime.now().replace(microsecond = 0))))
        now = datetime.datetime.now()
        self.SetTVPower()
        nextTime = now.replace(second = 0) + datetime.timedelta(weeks = 1)
        self.scheduler.enterabs(time.mktime(nextTime.timetuple()), 1, self.SetPowerOff, ())

    def GetFirstTime(self, now, day, hhmm, action):
        weekday = datetime.datetime.weekday(now)
        days = day - weekday
        if days < 0:
            days += 7
        if hhmm:
            hh, mm = hhmm.split(':')
            firstTime = now.replace(hour = int(hh), minute = int(mm), second = 0, microsecond = 0) -\
                datetime.timedelta(weeks = 1) + datetime.timedelta(days = days)
            while firstTime < now:
                firstTime += datetime.timedelta(weeks = 1)
            event = self.scheduler.enterabs(time.mktime(firstTime.timetuple()), 1, action, ())
            print(datetime.datetime.fromtimestamp(event.time), str(event.action).split(' ')[2])
            return firstTime
        else:
            return None

    def Schedule(self):
        self.on = None
        now = datetime.datetime.now()
        weekday = datetime.datetime.weekday(now)
        settings = ((self.morningOn, True), \
                    (self.morningOff, False), \
                    (self.eveningOn, True), \
                    (self.eveningOff, False))
        times = self.morningOn + self.morningOff + self.eveningOn + self.eveningOff
        actions = [self.SetPowerOn] * 7 + [self.SetPowerOff] * 7 + \
            [self.SetPowerOn] * 7 + [self.SetPowerOff] * 7
        onOff = [True] * 7 + [False] * 7 +[True] * 7 + [False] * 7
        days = list(range(0, 7)) * 4
        best = 999888777
        for time, action, on, day in zip(times, actions, onOff, days):
            firstTime = self.GetFirstTime(now, day, time, action)
            if firstTime:
                delta = (firstTime - now).total_seconds() # how far in the future
                if delta >=0 and delta < best:
                    best = delta
                    self.on = not on
                    #print('Set', self.on)
        self.SetTVPower()
    '''
    def ToggleSound(self):
        self.VolumeUp = not self.VolumeUp
        if self.VolumeUp:
            command = '/bin/echo volup | cec-client -s -d 1'
        else:
            command = '/bin/echo voldown | cec-client -s -d 1'
    '''
def doCmd(command, debug = False):
    if debug: print('doCmd:', command)
    result = subprocess.run(command, shell = True, stdout = subprocess.PIPE, stderr=subprocess.STDOUT)
    if debug: print(result.returncode, ':', result.stdout.decode('utf-8'))
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
    scheduler = sched.scheduler(time.time, time.sleep)
    power = Power(scheduler)
    slides = SlideTimer(scheduler, power)
    slides.Schedule(frequency = 1 * 60)
    power.Schedule()

    print(len(scheduler.queue))
    #print(scheduler.queue)
    for event in scheduler.queue:
        print(datetime.datetime.fromtimestamp(event.time), str(event.action).split(' ')[2])

    scheduler.run()

if __name__ == '__main__':
  main()
