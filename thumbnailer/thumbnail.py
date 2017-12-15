#!/usr/bin/python
from stat import *
from os import listdir,makedirs, walk, stat
from threading import Thread
from Queue import Queue, Empty
from time import sleep


workers = 16
sizes = ( ( 3840, 2560), ( 1920, 1280 ), ( 800, 600) )
#sizes = ( ( 3840, 2560 ),  ( 800, 600) )

ends = [ '.jpg', '.jpeg', '.gif', '.png' ]
srcPath = "./"

q = Queue()

for x,y in sizes:
    try:
        makedirs("./resize_%s" % x)
    except:
        pass

for dir, dirs, files in walk(srcPath):
    if dir != "./":
        continue;
    if dir.startswith("resize_"):
        print "skipping thumbnail dir %s" % dir
        continue;

    files.sort()
    for f in files:
        for suffix in ends:
            if f.lower().endswith(suffix):
                imgSrc  = "%s/%s" % (dir,f)
                print "checking %s" % (imgSrc)
                for x,y in sizes:
                    imgDest = "%s/resize_%s/%s" % (dir, x, f.lower().replace(' ','_'))
                    try :
                        if stat(imgSrc)[ST_CTIME] <= stat(imgDest)[ST_CTIME]:
                            print "skipping %s" % ( imgSrc)
                            continue
                    except OSError, err:
                        #print "error? %s" % err
                        pass
                    q.put([imgSrc, imgDest, x, y])

class Worker( Thread ):
    def run(self):
        import Image
        import PIL.ExifTags
        while True:
            try:
                imgSrc, imgDest, x, y = q.get(False)
            except Empty:
                return
            print imgSrc, x, y, q.qsize()

            img = Image.open(imgSrc)
            if hasattr(img, '_getexif'): # only present in JPEGs
                for orientation in PIL.ExifTags.TAGS.keys():
                    if PIL.ExifTags.TAGS[orientation]=='Orientation':
                        break

                e = img._getexif()       # returns None if no EXIF data
                if e is not None:
                    exif=dict(e.items())
                    try:
                        orientation = exif[orientation]

                        if   orientation == 3: img = img.transpose(Image.ROTATE_180)
                        elif orientation == 6: img = img.transpose(Image.ROTATE_270)
                        elif orientation == 8: img = img.transpose(Image.ROTATE_90)
                    except KeyError:
                        # cant find the rotation info, continue on
                        pass

            img.thumbnail((x,y), Image.ANTIALIAS)
            img.save(imgDest)

for x in xrange(workers):
    Worker().start()
while not q.empty():
    try:
        sleep(1)
    except:
        # keyboard interrupt
        while not q.empty():
            q.get(False)

print "done"
