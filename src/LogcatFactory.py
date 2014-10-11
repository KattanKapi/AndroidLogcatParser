from PyQt4.QtCore import *

#import PlainLogcat
#import LogcatVtime
#import LogcatVThreadtime


from LogcatVTime import *
from PlainLogcat import *
from LogcatVThreadTime import *

class LogcatFactory(QObject):

    def __init__(self):
        super(LogcatFactory,self).__init__()
        
    def identify(self, fileName):

        plainLogcat = PlainLogcat(fileName)
        ret = plainLogcat.identify()
        if ret == True:
            return plainLogcat
        else:
            del plainLogcat

        logcatVThreadTime = LogcatVThreadTime(fileName)
        ret = logcatVThreadTime.identify()
        if ret == True:
            return logcatVThreadTime
        else:
            del logcatVThreadTime
            
        logcatVTime = LogcatVTime(fileName)
        ret = logcatVTime.identify()
        
        if ret == True:
            return logcatVTime
        else:
            del logcatVTime

        print "Unknown file format"

        return None

