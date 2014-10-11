# -*- coding: utf-8 -*-
#imports:

#Select id from sometable where name like '%omm%'

import re
import operator
import os
import sys 
import time
import Queue
import threading
import random

from PyQt4.QtCore import * 
from PyQt4.QtGui import * 
from PyQt4 import QtCore, QtGui
from PyQt4.QtSql import *

from LogcatFactory import *
from PlainLogcat import *
from LogcatV import *

def main():
    # enable this for production release to get error logs
    #sys.stderr = open("Android_Workbench.log", 'w')
    app = QApplication(sys.argv) 
    w = AndroidWorkbenchMainWindow() 
    w.show() 
    sys.exit(app.exec_()) 

class AndroidWorkbenchMainWindow(QWidget): 
    def __init__(self, *args): 
        QWidget.__init__(self, *args) 

        #initilisation
        self.logcatObjects = []
        self.filterLevelList = []
        self.comboList = []
        self.workerTh = QThread()
        self.workerThToGetMaxLine = None

        #db
        self.dbFilename = self.genRandomDbName()
        self.db = QSqlDatabase.addDatabase("QSQLITE")
        self.db.setHostName("bigblue")
        self.db.setDatabaseName(self.dbFilename)
        self.db.setUserName("johnc")
        self.db.setPassword("johnc")

        # drag an drop support
        self.setAcceptDrops(True)
        
        self.setWindowTitle("Android workbench ... John J Chooracken<john.j.chooracken@accenture.com>")

        self.horizontalCheckboxLayout = QHBoxLayout()
        self.horizontalCheckboxLayout.addStretch(1)
        self.horizontalCheckboxLayout.setDirection(QBoxLayout.RightToLeft)
        self.horizontalCheckboxLayout.setAlignment(Qt.AlignLeft)

        self.horizontalSearchLayout = QHBoxLayout()
        self.horizontalSearchLayout.addStretch(1)
        self.horizontalSearchLayout.setDirection(QBoxLayout.RightToLeft)
        self.horizontalSearchLayout.setAlignment(Qt.AlignLeft)
        
        self.layout = QVBoxLayout()
        self.layout.addStretch(1)
        
        self.menubar = QtGui.QMenuBar(self)
        self.menubar.setEnabled(True)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 21))
        self.menuFile = self.menubar.addMenu("&File")
        self.menuFile.setSizeIncrement(QtCore.QSize(0, 0))
        self.menuEdit = self.menubar.addMenu("&Edit")
        self.layout.setMenuBar(self.menubar)
        self.menuFile.setTitle(QtGui.QApplication.translate("MainWindow", "File", None, QtGui.QApplication.UnicodeUTF8))
        self.menuEdit.setTitle(QtGui.QApplication.translate("MainWindow", "Help", None, QtGui.QApplication.UnicodeUTF8)) 

        #Creating Action Open File:
        self.fileopen = self.createAction("& Open File", self.openFileFn, "Ctrl+O", "", "Import data from a file")
        self.menuFile.addAction(self.fileopen)
        self.fileopen.setText(QtGui.QApplication.translate("MainWindow", "Open", None, QtGui.QApplication.UnicodeUTF8))

        #Creating Action Exit:
        self.exitAction = self.createAction("& Exit", self.exitFn, "Ctrl+E", "", "Exit from the application")
        self.menuFile.addAction(self.exitAction)
        self.exitAction.setText(QtGui.QApplication.translate("MainWindow", "Exit", None, QtGui.QApplication.UnicodeUTF8))        
        
        #Creating Action About:
        self.about = self.createAction("& About", self.aboutFn, None, "", "About this tool")
        self.menuEdit.addAction(self.about)
        self.about.setText(QtGui.QApplication.translate("MainWindow", "About", None, QtGui.QApplication.UnicodeUTF8))
        
        #Creating Action Version:
        self.version = self.createAction("& Version", self.versionFn, "Ctrl+V", "", "Version of this tool")
        self.menuEdit.addAction(self.version)
        self.version.setText(QtGui.QApplication.translate("MainWindow", "Version", None, QtGui.QApplication.UnicodeUTF8))
        
        # create table
        self.table = self.createTable() 
        self.layout.addWidget(self.table) 
        self.setLayout(self.layout) 

    # Shows "Quit, Jump, Copy" options when the user right clicks
    def popup(self, pos):
        #for i in self.table.selectionModel().selection().indexes():
        #    print i.row(), i.column()
        menu = QMenu()
        
        quitAction = menu.addAction("Quit")
        jumpAction = menu.addAction("Jump")
        copyAction = menu.addAction("Copy")
        
        action = menu.exec_(self.mapToGlobal(pos))
        
        if action == quitAction:
            self.exitFn()
            
        elif action == jumpAction:
            indexes = self.table.selectionModel().selection().indexes();
            self.updateUI("",False)
            #self.table.scrollTo(indexes[0].row(), indexes[0].column())
            
            row = indexes[0].row()
            nextIndex = self.table.model().createIndex(row,0)
            self.table.setCurrentIndex(nextIndex)
            self.table.scrollTo(nextIndex)
            self.table.scrollToBottom()
            
        elif action == copyAction:
            # There should be a better way than this hacked code 
            # Need to change this sometime later
            selected_text = ""
            highlightedRows = self.table.selectionModel().selectedIndexes()
            
            if (len(highlightedRows)/8) > 100:
                #show a message saying we cannot copy such a large amount into memory
                QtGui.QMessageBox.question(self, 'Message',"Cannot copy more than 100 rows at the same time", QtGui.QMessageBox.Ok, QtGui.QMessageBox.Ok)
                return
            
            tmp = []    
            tmp2 = []      
            for current in highlightedRows: 
                index = current.row(),current.column()    
                tmp.append(index)
                index = current.row(),current.column(),self.table.model().data(current).toString()
                tmp2.append(index)
            
            tmp = sorted(tmp)
            
            prev = tmp[0][0]
            for idx, i in enumerate(tmp):  
                for j in tmp2:
                    if j[0] == i[0] and j[1] == i[1]:
                        selected_text = selected_text + j[2]
                        if idx+1 < len(tmp):
                            if prev == tmp[idx+1][0]:
                                selected_text = selected_text + "\t"
                            else:
                                selected_text = selected_text + "\n"
                        
                                prev = tmp[idx+1][0]
                        
                        del j
                        break
            QApplication.clipboard().setText(selected_text)
                
    def aboutFn(self):
        QMessageBox.about(self,"Android Workbench", "Developer:\tJohn J Chooracken(johnjc@gmail.com)\nDetails:\t\tTool to parse logs generated from an Android device.\n\t\tSupports sqlite3 search query")

    def versionFn(self):
        QMessageBox.about(self,"Workbench version", "Android workbench version:\tv1.6")

    def exitFn(self):
        reply = QtGui.QMessageBox.question(self, 'Message',"Are you sure to quit?", QtGui.QMessageBox.Yes |QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.Yes:
            # Cleanup old db (if exists) and stop worker thread (if running)
            self.stopWorkerThreads()
            self.cleanupDb()
            sys.exit(1)
        else:
            pass

    def genRandomDbName(self):
        return "logcatdb." + str(time.time()) + "_" + str(random.SystemRandom(time.time()).random()) + ".sqlite3"

    # Handles drag and drop events
    def dropEvent(self,event):
        urls = event.mimeData().urls()

        if len(urls) == 0:
            return

        fileName = urls[0].toLocalFile();
        if len(fileName) == 0:
            return;

        self.startParsing(fileName)
        
    def dragEnterEvent(self, event):
        m = event.mimeData()
        if m.hasUrls():
            if os.path.isfile(m.urls()[0].toLocalFile()):
                event.acceptProposedAction()
                return

        event.ignore()
            
    # Initialises the DB and if a table does not exist then create it.
    def initDb(self):
        
        ok = self.db.open()
        if ok != True:
            QtGui.QMessageBox.information(self,"Error!","Db open error: "+ self.db.lastError().text())
            print >> sys.stderr,  self.db.lastError().text()
            sys.exit(-1)
        
        str = "CREATE TABLE IF NOT EXISTS logcat_row ( rowCtr INTEGER PRIMARY KEY, \
        level CHAR, time CHAR(25), pid INTEGER, tid INTEGER, application TEXT, tag TEXT, \
        text TEXT)"
        
        query = QSqlQuery()
        #query.exec_("PRAGMA synchronous=OFF")
        #query.exec_("PRAGMA temp_store=MEMORY")
        query.exec_(str)

    def closeEvent(self,event):
        print >> sys.stderr,  "Close event called"
        # Cleanup old db (if exists) and stop worker thread (if running)
        self.stopWorkerThreads()
        self.cleanupDb()        

    def clearLayout(self, layout):
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)

            if isinstance(item, QtGui.QWidgetItem):
                item.widget().close()
            elif isinstance(item, QtGui.QSpacerItem):
                pass
            else:
                self.clearLayout(item.layout())

            # remove the item from layout
            layout.removeItem(item) 

    # Called when the user selects a file for parsing via the File option menu
    def openFileFn(self):
        try:
            filename = unicode(QtGui.QFileDialog.getOpenFileName(self, 'Open File', '', ".txt .alog(*.txt *.alog)"))
            if filename != "":
                self.startParsing(filename)
            
        except IOError:
            pass

    # Do some book keeping and launch worker threads to start parsing and update the Db 
    def startParsing(self,fileName):

        # Cleanup old db (if exists) and stop worker thread (if running)
        self.stopWorkerThreads()
        self.cleanupDb()

        fileSize = os.stat(fileName).st_size/(1024*1024)
        
        if fileSize == 0:
            fileSize = os.stat(fileName).st_size/1024

            if fileSize == 0:
                fileSize = os.stat(fileName).st_size
                self.strFileSize = str(fileSize) + " bytes "
            else:
                self.strFileSize = str(fileSize) + " KB "
        else:
            self.strFileSize = str(fileSize) + " MB "
            
        self.dbFilename = self.genRandomDbName()
        self.db.setDatabaseName(self.dbFilename)
        self.initDb()
        self.reDrawLayout(fileName)

        self.workerTh = WorkerThread(fileName,self.logcatObjects)
        self.workerTh.setTerminationEnabled(True)
        self.connect( self.workerTh, QtCore.SIGNAL("finished()"), self.workerThreadFinished)
        self.connect( self.workerTh, QtCore.SIGNAL("terminated()"), self.workerThreadTerminated)
        self.connect( self.workerTh, QtCore.SIGNAL("updateRow(QString)"), self.updateRow )
        self.connect( self.workerTh, QtCore.SIGNAL("handleError(int)"), self.handleErrorsFromWorkerThread )
        
        self.workerTh.start()
        self.startTime = time.time()
            
        self.table.model().clear()
        self.table = self.createTable()
        self.layout.addWidget(self.table)     
        self.setWindowTitle("Android workbench ( " + fileName + " )")           
        
    # Called when the application is closed abruptly and informs the worker thread to stop
    # operating.
    def stopWorkerThreads(self):
        if self.workerTh.isRunning() == True :
            #indicate to the processing loop to quit
            print >> sys.stderr, "Worker Thread is running ... asking it to stop"
            self.workerTh.stop()
            self.workerTh.wait()
            self.workerTh = QThread()
        else:
            print >> sys.stderr, "Worker Thread is not running"
            
        if self.workerThToGetMaxLine != None and self.workerThToGetMaxLine.isRunning() == True :
            self.workerThToGetMaxLine.stop()
            self.workerThToGetMaxLine.wait()

    # delete the db as we exit out of the app?
    # Need to think if this is the right approach, is it possible we may need it again?
    def cleanupDb(self):

        self.db.commit()
        self.db.close()
        if os.path.exists(self.dbFilename):
            os.remove(self.dbFilename)
        else:
            print >> sys.stderr,  "cleanupDb:SQlite file does not exist"
        
    # called when search button is clicked
    def onSearchButtonClicked(self):
        #print >> sys.stderr,  "Search button clicked"
        self.updateUI(self.comboBox.currentText(),True) 
        
    def reDrawLayout(self, filename) :
        self.clearLayout(self.horizontalCheckboxLayout)
        self.clearLayout(self.layout)
        self.clearLayout(self.horizontalSearchLayout)
        
        self.filterLevelList[:] = []  

        self.cbF = QtGui.QCheckBox('F', self)
        self.cbF.toggle()                
        self.cbF.stateChanged.connect(self.searchFilterFChanged)                
        self.horizontalCheckboxLayout.addWidget(self.cbF)
        self.filterLevelList.append('F');

        self.cbE = QtGui.QCheckBox('E', self)
        self.cbE.toggle()                
        self.cbE.stateChanged.connect(self.searchFilterEChanged)
       
        self.horizontalCheckboxLayout.addWidget(self.cbE)
        self.filterLevelList.append('E');

        self.cbD = QtGui.QCheckBox('D', self)
        self.cbD.toggle()                
        self.cbD.stateChanged.connect(self.searchFilterDChanged)                
        self.horizontalCheckboxLayout.addWidget(self.cbD)
        self.filterLevelList.append('D');

        self.cbW = QtGui.QCheckBox('W', self)
        self.cbW.toggle()                
        self.cbW.stateChanged.connect(self.searchFilterWChanged)
        self.horizontalCheckboxLayout.addWidget(self.cbW)
        self.filterLevelList.append('W');

        self.cbV = QtGui.QCheckBox('V', self)
        self.cbV.toggle()                
        self.cbV.stateChanged.connect(self.searchFilterVChanged)
        self.horizontalCheckboxLayout.addWidget(self.cbV)
        self.filterLevelList.append('V');

        self.cbI = QtGui.QCheckBox('I', self)
        self.cbI.toggle()                
        self.cbI.stateChanged.connect(self.searchFilterIChanged)
        self.horizontalCheckboxLayout.addWidget(self.cbI)
        self.filterLevelList.append('I');              
        

        self.statsLabel = QtGui.QLabel()
        self.statsLabel.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.statsLabel.setText("File size = "+ self.strFileSize+ "\tParsing time = 0 sec")
        self.statsLabel.setAlignment(Qt.AlignLeft)
        self.horizontalCheckboxLayout.addWidget(self.statsLabel)
        self.layout.addLayout(self.horizontalCheckboxLayout)
                

        self.btn = QPushButton('Search',self)
        self.btn.setToolTip('Updates the UI based on the search result')
        self.btn.setAutoDefault(True)
        self.btn.setDefault(True)
        self.connect( self.btn, SIGNAL("clicked()"), self.onSearchButtonClicked )
        self.horizontalSearchLayout.addWidget(self.btn,0,Qt.AlignRight)


        self.comboBox = QComboBox()
        self.comboBox.addItems(self.comboList)
        self.comboBox.connect(self.comboBox, QtCore.SIGNAL('activated(QString)'), self.onTextActivated)
        self.comboBox.connect(self.comboBox, QtCore.SIGNAL('editTextChanged(QString)'), self.handleEmptySearchBox)
        self.comboBox.setAutoCompletionCaseSensitivity(True)
        self.comboBox.setEditable(True)
        self.horizontalSearchLayout.addWidget(self.comboBox,10)


        self.layout.addLayout(self.horizontalSearchLayout)

        self.progressbar = QProgressBar()
        self.progressbarCtr = 0
        self.progressbar.setMinimum(self.progressbarCtr)
        
        # This could potentially freeze the UI if the size of file is large
        # this is a hack. We find out the file size if file size is greater than 
        # 50 Mb then we give a random big number and then get the number of lines
        # information from  a separate thread
        
        fileSize = os.stat(filename).st_size
        
        if (fileSize > 50*1024*1024):
            #set the maxCtr to some sensible value and let a worker thread 
            #update it with the correct value
            self.progressbarMaxCtr = 300000
            
            self.workerThToGetMaxLine = WorkerThreadToGetMaxLine(filename)
            self.workerThToGetMaxLine.setTerminationEnabled(True)
            self.connect( self.workerThToGetMaxLine, QtCore.SIGNAL("updateNumofLines(int)"), self.workerThToGetMaxLineFinished)
            self.connect( self.workerThToGetMaxLine, QtCore.SIGNAL("terminated()"), self.workerThToGetMaxLineTerminated)
            self.workerThToGetMaxLine.setPriority(QThread.TimeCriticalPriority)
            self.workerThToGetMaxLine.start()
        else:        
            self.progressbarMaxCtr = max(enumerate(open(filename,'rb')))[0] or 100
            
        print >> sys.stderr, "No. of lines in file  = " + str(self.progressbarMaxCtr)
        self.progressbar.setMaximum(self.progressbarMaxCtr or 100)
        self.progressbar.setValue(self.progressbarCtr)
        self.layout.addWidget(self.progressbar)


    def workerThToGetMaxLineTerminated(self):
        pass
    
    def workerThToGetMaxLineFinished(self, maxLines):
        self.progressbarMaxCtr = maxLines
        self.progressbar.setMaximum(self.progressbarMaxCtr)
        
    
    def workerThreadTerminated(self):
        print >> sys.stderr,  "Inside the \"workerThreadTerminated\" callback signal"
        
    def workerThreadFinished(self):
        self.updateUI(self.comboBox.currentText(),False)
        self.progressbar.setValue(self.progressbarMaxCtr)
        
        self.statsLabel.setText("File size = "+ self.strFileSize+"\tParsing time = " + str(time.time() - self.startTime) + " sec")

    def handleErrorsFromWorkerThread(self,errorCode):
        print "handleErrorsFromWorkerThread"
        if errorCode == 1:
            #Stop the worker thread
            self.stopWorkerThreads()
            #display Unknown format to user
            QtGui.QMessageBox.question(self, 'Message',"Unknown file format!!!", QtGui.QMessageBox.Ok , QtGui.QMessageBox.Ok)
            
    def updateRow(self,text):
        #print "\nFinished updateRow\n"        
        self.updateUI(self.comboBox.currentText(),False)
        self.progressbarCtr = self.progressbarCtr + 10000
        self.progressbar.setValue(self.progressbarCtr)
        self.statsLabel.setText("File size = " + self.strFileSize + "\tParsing time = " + str(time.time() - self.startTime) + " sec")

        
    def onTextActivated(self, string):
        #check if this search string is already added to the list
        if string not in self.comboList:
            self.comboList.append(string)
            
        self.onSearchButtonClicked ()


    def handleEmptySearchBox(self, text):
        if len(text) == 0:
            self.updateUI("",False)
        
         
    def searchFilterIChanged(self, state):
        
        if state == QtCore.Qt.Checked:
            self.filterLevelList.append('I')
        else:
            self.filterLevelList.remove('I')

        self.updateUI("",False)

    def searchFilterVChanged(self, state):
        
        if state == QtCore.Qt.Checked:
            self.filterLevelList.append('V')
        else:
            self.filterLevelList.remove('V')

        self.updateUI("",False)        

    def searchFilterWChanged(self, state):
        
        if state == QtCore.Qt.Checked:
            self.filterLevelList.append('W')
        else:
            self.filterLevelList.remove('W')

        self.updateUI("",False)

    def searchFilterDChanged(self, state):
        
        if state == QtCore.Qt.Checked:
            self.filterLevelList.append('D')
        else:
            self.filterLevelList.remove('D')

        self.updateUI("",False)
        

    def searchFilterEChanged(self, state):
        
        if state == QtCore.Qt.Checked:
            self.filterLevelList.append('E')
        else:
            self.filterLevelList.remove('E')

        self.updateUI("",False)

    def searchFilterFChanged(self, state):
        
        if state == QtCore.Qt.Checked:
            self.filterLevelList.append('F')
        else:
            self.filterLevelList.remove('F')

        self.updateUI("",False)


    def updateUI(self, strQuery, showErrorDialog):

        queryStr = 'SELECT * FROM logcat_row '
        whereClause = ""
        query = QSqlQuery(self.db)
        
        if len(strQuery) <= 0:
            if len(self.filterLevelList) > 0 :

                whereClause = "WHERE "
                ctr = len(self.filterLevelList)
                for i in self.filterLevelList:
                    ctr = ctr - 1;
                    whereClause = whereClause + "level='" + str(i) + "'"
                    if ctr > 0:
                        whereClause = whereClause + " OR "
                whereClause = whereClause + " "

            query.exec_(queryStr + whereClause)
        else:
            query.exec_(queryStr + "WHERE " + strQuery)

        
        if not self.table.model().setQuery(query):
            #print >> sys.stderr,  self.table.model().lastError().text()
            if (showErrorDialog and len(strQuery) > 0) and (len(self.table.model().lastError().text())> 1):
                QtGui.QMessageBox.information(self,"Error!","Check your search string: "+strQuery)
                self.comboList.remove(strQuery)
                self.comboBox.removeItem(self.comboBox.findText(strQuery))
                self.updateUI("",False)
                
      
    #A function to help us create Actions faster:
    def createAction(self,text, slot=None, shortcut=None, icon=None,
                     tip=None, checkable=False, signal="triggered()"):
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(QIcon(":/%s.png" % icon))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
        if slot is not None:
            self.connect(action, SIGNAL(signal), slot)
        if checkable:
            action.setCheckable(True)
        return action                                
    
    def createTable(self):
        # create the view
        tv = QTableView()

        query = QSqlQuery(self.db)
        query.exec_('SELECT * FROM logcat_row')

        tv.setContextMenuPolicy(Qt.CustomContextMenu)
        tv.customContextMenuRequested.connect(self.popup)
        
        model = QSqlQueryModel()
        if not model.setQuery(query):
            print >> sys.stderr,  model.lastError().text()

        model.setHeaderData(0, Qt.Horizontal, "Row Ctr")
        model.setHeaderData(1, Qt.Horizontal, "Level")
        model.setHeaderData(2, Qt.Horizontal, "Time")
        model.setHeaderData(3, Qt.Horizontal, "Pid")
        model.setHeaderData(4, Qt.Horizontal, "Tid")
        model.setHeaderData(5, Qt.Horizontal, "Application")
        model.setHeaderData(6, Qt.Horizontal, "Tag")
        model.setHeaderData(7, Qt.Horizontal, "Text")

        # set the table model
        tv.setModel(model)

        tv.horizontalHeader().setStretchLastSection(True)
        #tv.setItemDelegate(Delegate())

        # set the minimum size
        tv.setMinimumSize(800, 500)

        # hide grid
        tv.setShowGrid(False)
        
        # selection behaviour
        tv.setSelectionBehavior(QAbstractItemView.SelectRows);

        # set the font
        font = QFont("Courier New", 8)
        tv.setFont(font)

        # hide vertical header
        vh = tv.verticalHeader()
        vh.setVisible(False)

        # set horizontal header properties
        hh = tv.horizontalHeader()
        hh.setStretchLastSection(True)

        # set column width to fit contents
        tv.resizeColumnsToContents()

        # set row height
        nrows = len(self.logcatObjects)
        for row in xrange(nrows):
            tv.setRowHeight(row, 18)

        # enable sorting
        #tv.setSortingEnabled(True)

        return tv

# Responsibility of this thread is to find out the number of lines/records
# in a big file. This is needed since some logcat logs (monkey output)
# are > 50 MB and  to figure out the size within the main GUI thread would
# lead to bad end user experience.

# Note: This thread is only created when the file size is > 50 MB. If its <50 MB
# finding out the number of lines/records is done within the context of the UI thread

class WorkerThreadToGetMaxLine(QtCore.QThread):
    def __init__(self, fileName):
        QtCore.QThread.__init__(self)
        self.fileName = fileName
        self.stopWorking = False
        

    def stop(self):
        print "WorkerThreadToGetMaxLine: Stop called"
        self.stopWorking = True
                    
    def run(self):        
        #lines = max(enumerate(open(self.fileName,'rb')))[0] or 100
        lines = 0
        try:
            print self.fileName
            with open(self.fileName,"rb") as f:
                for line in f:
                    lines += 1
                    if (self.stopWorking == True):
                        break                
        except:
            e = sys.exc_info()[0]
            print >> sys.stderr,  e
            
        self.emit( QtCore.SIGNAL('updateNumofLines(int)'), lines)


# My workhorse :). Responsibility of this thread  is to identify the type of file being parsed
# and then parse it and write the output to a sqlite3 db. At regular intervals it also sends
# signals to the UI thread to update the progress

# Note: This is based on Factory design pattern. Since output of adb logcat can have different
# formats we have an extensible framework in place. 
# LogcatFactory identify would return the type of logcat object
# TODO: Remove identify function and hide this as part of the constructor.
  
class WorkerThread(QtCore.QThread):
    def __init__(self, fileName, logcatObjects):
        QtCore.QThread.__init__(self)
        self.fileName = fileName
        self.stopWorking = False
        

    def run(self):       
            
        print >> sys.stderr,  "Inside workerThread"

        factory = LogcatFactory ()
        self.logcatParserObj = factory.identify(self.fileName)

        if self.logcatParserObj != None:
            self.connect( self.logcatParserObj, QtCore.SIGNAL("update(QString)"), self.update)
            try:
                self.logcatParserObj.parse()
            except:
                e = sys.exc_info()[0]
                print >> sys.stderr,  e
                
            print >> sys.stderr,  "Finished parsing the log file"
        else:
            # Handle unknown file format
            self.emit(QtCore.SIGNAL('handleError(int)'),1)
            
    def stop(self):
        print "WorkerThread:Stop called"
        if self.logcatParserObj != None:
            self.logcatParserObj.stop()

    def update(self,string):
        #print "\nreceived ...\n"
        self.emit( QtCore.SIGNAL('updateRow(QString)'), "from worker thread " )
    

    
if __name__ == "__main__": 
    main()





########################### deprecated code #################################

# Not used any more. This was based on an old architecture         
class MyTableModel(QAbstractTableModel): 
    def __init__(self, datain, headerdata, parent=None, *args): 
        """ datain: a list of lists
            headerdata: a list of strings
        """
        QAbstractTableModel.__init__(self, parent, *args) 
        self.arraydata = datain
        self.headerdata = headerdata

        #print >> sys.stderr,  self.headerdata

 
    def rowCount(self, parent):
        return len(self.arraydata) 
 
    def columnCount(self, parent): 
        return 7 #len(self.arraydata[0]) 
 
    def data(self, index, role): 
        try:
            if not index.isValid(): 
                return QVariant() 
            elif role != Qt.DisplayRole: 
                return QVariant()

            #print >> sys.stderr,  index.row()
            #print >> sys.stderr,  index.column()
            return QVariant(self.arraydata[index.row()][index.column()]) 
        except IndexError:
            pass


    def clear(self):
       
        self.arraydata = []
        #print >> sys.stderr,  len(self.arraydata)
        self.emit(SIGNAL('dataChanged(const QModelIndex &,const QModelIndex &)'), QModelIndex(), QModelIndex())
        
    def setData(self, datain):
        self.emit(SIGNAL("layoutAboutToBeChanged()"))
        self.arraydata = datain
        #print >> sys.stderr,  len(self.arraydata)
        #self.emit(SIGNAL('dataChanged(const QModelIndex &,const QModelIndex &)'), QModelIndex(), QModelIndex())
        self.emit(SIGNAL("layoutChanged()"))        
        
        
    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return QVariant(self.headerdata[col])
        return QVariant()

    def sort(self, Ncol, order):
        """Sort table by given column number.
        """
        self.emit(SIGNAL("layoutAboutToBeChanged()"))
        self.arraydata = sorted(self.arraydata, key=operator.itemgetter(Ncol))        
        if order == Qt.DescendingOrder:
            self.arraydata.reverse()
        
        self.emit(SIGNAL("layoutChanged()"))

class Delegate(QItemDelegate):
    row_to_highlight = []
    def __init__(self, parent=None, *args): 
        QItemDelegate.__init__(self,parent,*args)
 
    def highlight_row(self,painter,option,index):
        painter.save()
        # set background color
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(QColor(255,102,102)))
        painter.drawRect(option.rect)

        # set text color
        painter.setPen(QPen(Qt.black))
        value = index.data(Qt.DisplayRole)
        if value.isValid():
            text = value.toString()
            painter.drawText(option.rect, Qt.AlignLeft, text)
            
        painter.restore()
        
    def paint(self,painter, option,index):

        if index.column() == 0:
            val = index.data()
            val = val.toPyObject()
            if val == 'E' or val == 'F':
                Delegate.row_to_highlight.append(index.row())
                self.highlight_row(painter,option,index)
            else:
                QItemDelegate.paint(self,painter, option, index);
        else:
            if index.row() in Delegate.row_to_highlight:
                self.highlight_row(painter,option,index)
            else:
                QItemDelegate.paint(self,painter, option, index);
        

