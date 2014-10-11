from PyQt4.QtCore import *
from PyQt4 import QtCore, QtGui
from PyQt4.QtSql import *
import re


class PlainLogcat(QObject):
    def __init__(self, fileName):
        self.mFileName = fileName
        self.mStopWorking = False
        super(PlainLogcat,self).__init__()

    # Logic is to parse first 10 lines and see the success rate. If its > 70% then we believe this 
    # is a particular file type.
    # If during the first pass, success % < 70 then we do another pass before we give up. This
    # is because sometimes the first 10 lines contain some vendor specific logs which does not 
    # confirm to well know patterns.
    # TODO: this could be moved to some base class. 
    def identify(self):
        print "PlainLogcat" + self.mFileName
        ctr = 0
        passCtr = 0
        itr = 0
        
        with open(self.mFileName,'rb') as f:
            for line in f:
                line = re.sub('[\r\n]','',line)
                s1 =  re.findall(r'[a-zA-Z]/.*[\s]*\([\s]*\d*\): .*',line)
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


        if passCtr >= 7:
            print "PlainLogcat TRUE"
            return True
        else:
            print "PlainLogcat FALSE"
            return False


    def stop(self):
        self.mStopWorking = True

# Parse and add it to a sqlite db.
# TODO: improve the parsing and db commit speed
# Had a different architecture where parsing was done in one thread and db commit was done
# in another thread but the performance was worse. So sticking with this solution until I find out
# why the performance degraded instead of improving!
    def parse(self):
        ctr = 0
        primaryCtr = 0
        query = QSqlQuery()

        #query.exec_("PRAGMA synchronous=OFF")
        #query.exec_("PRAGMA temp_store=MEMORY")
        
        query.prepare("INSERT INTO logcat_row (rowCtr,level,time,pid,tid,application,tag,text) \
        VALUES (:rowCtr,:level,:time,:pid,:tid,:application,:tag,:text)")

        with open(self.mFileName,'rb') as f:
            for line in f:
                if ctr == 0:
                    QSqlDatabase.database().transaction();
    
                ctr = ctr + 1
                primaryCtr = primaryCtr + 1

                try :
                    #print >> sys.stderr,  re.findall(r'[a-zA-Z]/.*[\s]*\([\s]*\d*\): .*',line)
                    time = "" # re.findall(r'^(\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{3})',line)
                    application =  re.findall(r'[a-zA-Z]/.*?[\s]*\([\s]*\d*\):',line)
                    #print >> sys.stderr,  "applicaion = " + str(application).strip('[]\'')
                    #print >> sys.stderr,  "\n"
                    tmp_list = re.split('[/(\(\s*)(\):)]',str(application).strip('[]\''))
                    #level = re.findall(r'[a-zA-Z]/',str(application).strip('[]'));
                    #pid = re.findall(r'\([\s]*\d*\)',str(application).strip('[]'))
                    tmp_list = filter (lambda a: a != '', tmp_list)
                    level = []
                    application = []
                    pid = []

                    if len(tmp_list) >= 3:
                        level.append(tmp_list[0])
                        application.append(tmp_list[1])
                        pid.append(tmp_list[2])
                    elif len(tmp_list) == 2:
                        level.append(tmp_list[0])
                        if tmp_list[1].isdigit() == True:
                            pid.append(tmp_list[1])
                            application.append("")
                        else:
                            application.append(tmp_list[1])
                            pid.append("")
                except:
                    print >> sys.stderr,  "first level"
                    e = sys.exc_info()[0]
                    print >> sys.stderr,  e


                #print primaryCtr,level,time,pid,application                    
                text = re.findall(r'\): .*',line)


                try:    

                    query.bindValue(":rowCtr",primaryCtr)
                except:
                    query.bindValue(":rowCtr",-1)

                try:
                    query.bindValue(":level",str(level).strip('[]\'') or "?")
                except:
                    query.bindValue(":level","?")

                try:
                    query.bindValue(":time",str(time).strip('[]\'') or "")
                except:
                    query.bindValue(":time","?")

                try:
                    query.bindValue(":pid",int(str(pid).strip('[]\'')) or 0)
                except:
                    query.bindValue(":pid",0)

                try:
                    query.bindValue(":tid",int(str([""]).strip('[]\'') or 0))
                except:
                    query.bindValue(":tid",0)

                try:
                    query.bindValue(":application",str(application).strip('[]\'') or "?")
                except:
                    query.bindValue(":application","?")

                try:
                    query.bindValue(":tag",str([""]).strip('[]\'') or "?")
                except:
                    query.bindValue(":tag","?")
                    
                try:
                    strText = (str(text).strip('[]\'').replace('\\t','    ') or "?")
                    strText = strText.replace('\\r','')
                    strText = strText
                    if len(strText) > 3:
                        strText = strText[3:]

                    query.bindValue(":text",strText or "?")

                except:
                    query.bindValue(":text","?")

                query.exec_()

                #print primaryCtr
                if ctr == 10000:
                    QSqlDatabase.database().commit();
                    try:
                        self.emit( QtCore.SIGNAL('update(QString)'), "from worker thread " )                  
                        ctr = 0
                        #print "\nemitted \n"
                    except:
                        e = sys.exc_info()[0]
                        print >> sys.stderr,  e


                    
                # Check this flag at the end rather than at the begining
                # for a clean exit
                if self.mStopWorking == True:
                    print >> sys.stderr, "master asked me to stop working !!! "
                    break                  

            print "finished"
            QSqlDatabase.database().commit();
            self.emit( QtCore.SIGNAL('updateRow(QString)'), "from worker thread " )
            ctr = 0
