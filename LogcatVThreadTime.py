
from PyQt4.QtCore import *
from PyQt4 import QtCore, QtGui
from PyQt4.QtSql import *
import re

class LogcatVThreadTime(QObject):
     #re.findall(r'^(\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{3}   \d{3}   \d{3} [A-Za-z] [0-9A-Za-z\.\$\\/]*[ ]*?:.*)',"10-30 10:31:19.231   126   126 D gpsd    : RildRrlp::RildClientModuleRrlpAsn1()")
    def __init__(self, fileName):
        self.mFileName = fileName
        self.mStopWorking = False
        super(LogcatVThreadTime,self).__init__()        

    # Logic is to parse first 10 lines and see the success rate. If its > 70% then we believe this 
    # is a particular file type.
    # If during the first pass, success % < 70 then we do another pass before we give up. This
    # is because sometimes the first 10 lines contain some vendor specific logs which does not 
    # confirm to well know patterns.
    # TODO: this could be moved to some base class. 
    def identify(self):
        print self.mFileName
        ctr = 0
        passCtr = 0
        itr = 0
        with open(self.mFileName,'rb') as f:
            for line in f:
                line = re.sub('[\r\n]','',line)
                s1 =  re.findall(r'^(\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{3}[ ]+?\d+?[ ]+?\d+? [A-Za-z] [^\t\n\r\f\v]*?[ ]*?:.*)',line)                
                tmpstr = ""
                if len(s1) > 0:
                    tmpstr = s1[0]
                    tmpstr = re.sub('[\r\n]','',tmpstr)

                
                if tmpstr == line:
                    #print "pass"
                    passCtr = passCtr + 1
                else:
                    #print repr(tmpstr)
                    #print repr(line)
                    #print "fail"
                    pass
                ctr = ctr + 1
                if ctr >= 10:
                    #check if passCtr >=7 if its not then try one more iteration
                    # we should have a base class for this!
                    itr = itr + 1
                    if itr < 2:
                        if passCtr <=7:
                            passCtr = 0
                            ctr = 0
                    else:
                        break

        print passCtr
        if passCtr >= 7:
            print "LogcatVThreadTime True"
            return True
        else:
            print "LogcatVThreadTime False"
            return False

    def stop(self):
        self.mStopWorking = True

# Parse and add it to a sqlite db.
# TODO: improve the parsing and db commit speed
# Had a different architecture where parsing was done in one thread and db commit was done
# in another thread but the performance was worse. So sticking with this solution until I find out
# why the performance degraded instead of improving!
    def parse(self):
        
        filename = self.mFileName
        print filename
        ctr = 0
        primaryCtr = 0
        query = QSqlQuery()

        #query.exec_("PRAGMA synchronous=OFF")
        #query.exec_("PRAGMA temp_store=MEMORY")
        
        query.prepare("INSERT INTO logcat_row (rowCtr,level,time,pid,tid,application,tag,text) \
        VALUES (:rowCtr,:level,:time,:pid,:tid,:application,:tag,:text)")

        with open(filename,'rb') as f:
            for line in f:
                if ctr == 0:
                    QSqlDatabase.database().transaction();
                    
                ctr = ctr + 1
                primaryCtr = primaryCtr + 1

                time = "?"
                try :
                    #print >> sys.stderr,  re.findall(r'\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{3} [a-zA-Z]/.*[\s]*\([\s]*\d*\): .*',line)
                    s1 =  re.findall(r'^(\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{3}[ ]+?\d+?[ ]+?\d+? [A-Za-z] [^\t\n\r\f\v]*?[ ]*?:.*)',line)
                    s2 = r'([ ]+\d+?[ ]+\d+? [A-Za-z] [^\t\n\r\f\v]*?[ ]*?:.*)'
                    if len(s1) > 0:
                        time = s1[0].strip('\"\"');
                        time = time.strip('\'\'');
                        time = re.sub(s2,'',time)                        
                except:
                    print >> sys.stderr,  "first level"
                    e = sys.exc_info()[0]
                    print >> sys.stderr,  e

                #print line
                pid = "?"
                try :

                    s1 = re.findall(r'(   \d+?[ ]+?\d+? [A-Za-z] [^\t\n\r\f\v]*?[ ]*?:.*)', line)
                    s2 = r'([ ]+?\d+? [A-Za-z] [^\t\n\r\f\v]*?[ ]*?:.*)'
                    #s1 = re.findall(r'([ ]{1,3}\d+?[ ]+?\d*? )', line)
                    #s1 = re.findall(r'([ ]{1,3}\d+?[ ]{1,3}\d*? )', line)
                    #print s1
                    #if len(s1) > 0:
                    #    pid = s1[0].strip()
                    

                    if len(s1) > 0:
                        pid = s1[0].strip('\"\"');
                        pid = pid.strip('\'\'');
                        pid = re.sub(s2,'',pid)
                        #pid = re.sub(s2,'',str(s1).strip('[\"\"]')).strip()
                    #if ctr == 3516:
                    #    print "Line = " + line
                    #    print "S1 = " + str(s1)
                    #    print "Pid = " + pid                                            
                except:
                    print >> sys.stderr,  "2first level"
                    e = sys.exc_info()[0]
                    print >> sys.stderr,  e

                tid = "?"                    
                try :
                    s1 = re.findall(r'([ ]+\d+? [A-Za-z] [^\t\n\r\f\v]*?[ ]*?:.*)', line)
                    s2 = r'( [A-Za-z] [^\t\n\r\f\v]*?[ ]*?:.*)'
#                    tid = re.sub(s2,'',str(s1).strip('[\"\"]')).strip()
                    if len(s1) > 0:
                        tid = s1[0].strip('\"\"');
                        tid = tid.strip('\'\'');
                        tid = re.sub(s2,'',tid)                    
                except:
                    print >> sys.stderr,  "3first level"
                    e = sys.exc_info()[0]
                    print >> sys.stderr,  e
                    

                level="?"
                try :
                    s1 = re.findall(r'([A-Za-z] [^\t\n\r\f\v]*?[ ]*?:.*)', line)
                    s2 = r'( [^\t\n\r\f\v]*?[ ]*?:.*)'
                    #level = re.sub(s2,'',str(s1).strip('[\"\"]')).strip()
                    if len(s1) > 0:
                        level = s1[0].strip('\"\"');
                        level = level.strip('\'\'');
                        level = re.sub(s2,'',level)                     
                except:
                    print >> sys.stderr,  "4first level"
                    e = sys.exc_info()[0]
                    print >> sys.stderr,  e
                    

                application="?"
                try :
                    s1 =  re.findall(r'([A-Za-z] [^\t\n\r\f\v]*?[ ]*?:.*)',line)
                    s2=r'([ ]*?:[ ]+.*)'
                    #application = re.sub(s2,'',str(s1).strip('[\"\"]')).strip()
                    if len(s1) > 0:
                        application = s1[0].strip('\"\"');
                        application = application.strip('\'\'');
                        application = re.sub(s2,'',application)
                        #'D BrcmGps1Ri1ldIpc'
                        #strip level out of it
                        s1 = r'([A-Za-z] )'
                        application = re.sub(s1,'',application)
                except:
                    print >> sys.stderr,  "5first level"
                    e = sys.exc_info()[0]
                    print >> sys.stderr,  e

                text = "?"                    
                try :

                    text =  re.findall(s2,line)
                    if len(text) > 0 :
                        text = text[0]
                        s1=r'(^[ ]*: )'
                        text = re.sub(s1,'',text)
 
                except:
                    print >> sys.stderr,  "6first level"
                    e = sys.exc_info()[0]
                    print >> sys.stderr,  e
                    print text
                    
                try :

                    time = time.strip()
                    pid = pid.strip()
                    tid= tid.strip()
                    level = level.strip()
                    application = application.strip()
                    text = str(text).strip('[\'\']')
                except:
                    print text
                    print >> sys.stderr,  "7first level"
                    e = sys.exc_info()[0]
                    print >> sys.stderr,  e


                
                #print primaryCtr,level,time,pid,application
                try:    

                    query.bindValue(":rowCtr",primaryCtr)
                except:
                    query.bindValue(":rowCtr",-1)

                try:
                    query.bindValue(":level",level)
                except:
                    query.bindValue(":level","?")

                try:
                    query.bindValue(":time",time)
                except:
                    query.bindValue(":time","?")

                try:
                    query.bindValue(":pid",int(pid) or 0)
                except:
                    query.bindValue(":pid",0)

                try:
                    query.bindValue(":tid",int(tid) or 0)
                except:
                    query.bindValue(":tid",0)

                try:
                    query.bindValue(":application",application or "?")
                except:
                    query.bindValue(":application","?")

                try:
                    query.bindValue(":tag","" or "?")
                except:
                    query.bindValue(":tag","?")
                    
                try:
                    
                    strText = (text.replace('\\t','    ') or "?")
                    strText = strText.replace('\\r','')
                    #strText = re.split(':',strText,1)
                    
                    query.bindValue(":text",strText or "?")

                except:
                    query.bindValue(":text","?")

                query.exec_()
                    
                #print primaryCtr
                if ctr == 10000:
                    QSqlDatabase.database().commit();
                    self.emit( QtCore.SIGNAL('update(QString)'), "from worker thread " )
                    ctr = 0
                # Check this flag at the end rather than at the begining
                # for a clean exit
                if self.mStopWorking == True:
                    print >> sys.stderr, "master asked me to stop working !!! "
                    break
            print "finished"
            QSqlDatabase.database().commit();
            self.emit( QtCore.SIGNAL('update(QString)'), "from worker thread " )
            ctr = 0
