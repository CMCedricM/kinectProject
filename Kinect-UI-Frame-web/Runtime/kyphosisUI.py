import sys

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QDialog, QApplication


# Resources 
from Runtime.programRuntimes.kyphosis import Kyphosis
from Resources.UIResources.UI.kyphosisUI import kyphosisControlUI, avgKyphosisUI, KyphosisIndexUI



class kyphosisControl(QDialog): 
    def __init__(self): 
        super(kyphosisControl, self).__init__()
        self._Window = kyphosisControlUI.Ui_Dialog()
        self._Window.setupUi(self)

        # Name and Patient Id Vars 
        self._Name, self._PtId = None, None 

        # Kyphosis Class Instance 
        self._KyphosisProgram, self._KyphosisThread = Kyphosis(), None
        # Database/Web Req reference so we can logout when program is done
        self._DatabaseRef = None  

        # Other Windows To Display Kyphosis 
        self._CurrKyphWindow, self._AvgKyphWindow = window_Curr_Kyph(), window_Avg_Kyph() 
        # General UI Setup 
        self.connectButtons()
        self.setupThreads()
        self.connectSignals()


    def connectButtons(self): 
        self._Window.pushButton.clicked.connect(self.runAnalyzation) # Analyze Button
        self._Window.pushButton_2.clicked.connect(self.captureImg) # Capture Button
        self._Window.pushButton_3.clicked.connect(self.resetSpinePoints) # Reset Points Button
        self._Window.pushButton_4.clicked.connect(self.closeProgram) # Done Button 
        
        # Disable Certain Buttons Until Allowed 
        self._Window.pushButton.setDisabled(True)


    def setupThreads(self): 
        self._KyphosisThread = QThread()
        self._KyphosisProgram.moveToThread(self._KyphosisThread)
        self._KyphosisThread.start()

    def connectSignals(self): 
        self._KyphosisProgram.signalControlWindowtoShow.connect(self.show)
        self._KyphosisProgram.signalReqPtsSatisfied.connect(self.takeInput)
        self._KyphosisProgram.signalMessageOutput.connect(self.displayMessage)
        
        self._KyphosisProgram.signalKyphosisIndex.connect(self.displayCurrKyphosis)
        self._KyphosisProgram.signalProgramEnding.connect(self.displayAvgKyphosis)

        # Signals from kyphosis display Windows 
        self._CurrKyphWindow.optionSelectedSignal.connect(self.handleResetOrKeepPts)
        self._AvgKyphWindow.exitPressed.connect(self.programClosing) 

    
    
    
    def setPtInfoNStart(self,ptID, ptName, databaseHolder = None):
        self._KyphosisProgram.setPatientInfo((ptID, ptName))
        self._DatabaseRef = databaseHolder # We have to do this so that we can logout when the program is done
        self._KyphosisProgram.setDatabaseInstance(self._DatabaseRef)
        self._KyphosisProgram.runtime()



    def takeInput(self, boolVal): 
        if boolVal: 
            self._Window.pushButton.setDisabled(False)
        else: 
            self._Window.pushButton.setDisabled(True)

    def runAnalyzation(self): 
        self._Window.pushButton.setDisabled(True)
        self._KyphosisProgram._ProgramLog.output(2, "Beginning Analysis...")
        self._KyphosisProgram._RunCalculations = True 
    
    
    def captureImg(self): 
        self._KyphosisProgram._imgSave()
    
    
    def displayCurrKyphosis(self, kyphosisVal): 
       #print("Value: ", intVal)
       self._CurrKyphWindow.showCurrKyph(kyphosisVal)
       self._CurrKyphWindow.show()
    
    def handleResetOrKeepPts(self, intVal):
        if intVal == 0: 
            self._KyphosisProgram.reset(clearSpinalArr=False)
        elif intVal == 1: 
            self._KyphosisProgram.reset(clearSpinalArr=True)
        
    
    def closeProgram(self): 
        self._KyphosisProgram._Is_Done = True
    
    def resetSpinePoints(self):
        self._KyphosisProgram.reset(clearSpinalArr=True)

    def displayAvgKyphosis(self, kyphosisAvg): 
        if kyphosisAvg < 0: 
            self.programClosing(True)
        else: 
            self._KyphosisProgram._OpenCVDepthHandler.closeAllWindows()
            self._AvgKyphWindow.displayAvgKyp(kyphosisAvg)
            self._AvgKyphWindow.show()
    
    
    def programClosing(self,boolVal): 
        self._KyphosisThread.quit()
        #self._KyphosisProgram._OpenCVDepthHandler.closeAllWindows()
        self._KyphosisThread.wait(20)
        self.close()
        self._DatabaseRef.logout()
        exit(0)
        


    def displayMessage(self, message): 
        self._Window.label.setText(f"{message}")

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.programClosing(True)
            

class window_Curr_Kyph(QDialog): 
    
    optionSelectedSignal = pyqtSignal(int)
    def __init__(self): 
        super(window_Curr_Kyph, self).__init__()
        self._Window = KyphosisIndexUI.Ui_Dialog()
        self._Window.setupUi(self)

        # Basic UI Setup 
        self.connectButtons()

    
    def connectButtons(self):
        self._Window.pushButton.clicked.connect(self.keepNContinue)
        self._Window.pushButton_2.clicked.connect(self.resetNContinue)

    def showCurrKyph(self, kyphosisIndex): 
        self._Window.label_2.setText(f"{round(kyphosisIndex,4)}")


    def keepNContinue(self): 
        self.optionSelectedSignal.emit(0)
        self.close()

    def resetNContinue(self): 
        self.optionSelectedSignal.emit(1)
        self.close()


    
class window_Avg_Kyph(QDialog): 
    
    exitPressed = pyqtSignal(bool)
    def __init__(self): 
        super(window_Avg_Kyph, self).__init__()
        self._Window = avgKyphosisUI.Ui_Dialog()
        self._Window.setupUi(self)

        # Average Kyphosis 
        self.AvgKyphosis = None 
        
        # Connect Button
        self._Window.pushButton.clicked.connect(self.closeProgram)
    
    def displayAvgKyp(self, kyphosisIndex): 
        self._Window.label_2.setText(f"{round(kyphosisIndex,4)}")
    
    def closeProgram(self): 
        self.exitPressed.emit(True)
        self.close()



if __name__ == "__main__":
    # Set all pyqt5 windows to retain their scaling
    if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    main = kyphosisControl()
    main.show()
    app.exec_()