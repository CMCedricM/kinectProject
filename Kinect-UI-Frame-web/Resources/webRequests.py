import traceback
import requests, sched, time
from PyQt5.QtCore import pyqtSignal, QThread

class WebReq(QThread): 
    webReqMessage = pyqtSignal(tuple)
    loginAllowed = pyqtSignal(bool)
    
    def __init__(self): 
        # Have to do this to allow emitting signals 
        QThread.__init__(self)
        # Vars to allow website access 
        self._Response, self._PostData, self._Data, self._AccessToken = None, None, None, None  
        self._email, self._Password, self._TwoFactorCode = None, None, None 
        
        # Kinect Data
        self._GaitData, self._KyphosisData = dict(), dict()
        # This tells whether we have already established a link to the site 
        self._ConnectionAttempted, self._ConnectionActive = False, False
        self.waitingForTwoFactorCode = False 
        self._uploadMaxAttempts = 10 
        self._timeBetweenSends = 2 
        
        # URL for login and refresh 
        self._Login_URL = 'https://www.healage.org/auth/login'
        self._Refresh_Login_URL = 'https://www.healage.org/auth/refresh'
        
        # URL for Gait and Kyphosis Data
        self._GAIT_URL  = 'https://www.healage.org/api/kinect-gait-speed'
        self._Kyphosis_URL = 'https://www.healage.org/api/kyphosis-index'
    
        self._Logout_URL = 'https://www.healage.org/auth/logout'
    
    def setUserPass(self, user : str, passwd : str): 
        self._email, self._Password = user, passwd
    
    
    
    
    def linkStart(self, token=None):
        returnVal = -1
        
        if self._email is None or self._Password is None: 
            self.webReqMessage.emit((-1, "Error UserName or Password is NULL!"))
        
        elif not self._ConnectionActive and not self.waitingForTwoFactorCode: 
            self._Response = requests.post(self._Login_URL, json={
                'email': self._email,
                'password': self._Password,
                })
            # Check if the login was Accepted
            if not self._Response.ok: 
                self.webReqMessage.emit((-1, f"Invalid User Name or Password"))
            else: 
                # Now Begin the Wait for a token
                self.waitingForTwoFactorCode, self._ConnectionAttempted = True, True  
                # Set the Return Val Which tells the UI what to do, returnVAl of 1 indicated waiting for token 
                returnVal = 1
                
        elif self._ConnectionAttempted and self.waitingForTwoFactorCode: 
            # Save the two factor code 
            self._TwoFactorCode = token
            # Post the two factor code  
            self._Response = requests.post(f"{self._Login_URL}/{self._TwoFactorCode}")
            # Verify Web Response
            if not self._Response.ok: 
                self.webReqMessage.emit((-1, f"Invalid User Name, Password, or Two Factor Code"))
                self._ConnectionAttempted, self.waitingForTwoFactorCode = False, False 
            else: 
                print("Success")
                # Get the access token 
                self._Data = self._Response.json()
                self._AccessToken = self._Data['accessToken']
                self._ConnectionActive, self._ConnectionAttempted, self.waitingForTwoFactorCode = True, False, False 
                # Set the return val, 0 indicates we're good to go
                returnVal = 0 
                
        elif self._ConnectionActive: 
            self._Response = requests.post(self._Refresh_Login_URL, cookies=self._Response.cookies)
            print("Attempting Access Refreshed!")
            if not self._Response.ok: 
                self.webReqMessage.emit((-1, f"Error, unable to refresh session!"))
                returnVal = 0 
            else: 
                self._Data = self._Response.json()
                self._AccessToken = self._Data['accessToken']
                returnVal = -1 
                print("Access Refresh Success!")
        
        return returnVal 
    
    
    def __sendGaitSpd(self): 
        if self._GaitData is None: 
            self.webReqMessage.emit((-1, f"Error No Gait Speed Data to Upload!"))
            return 
        
        currAttempt = 0 
         
        while True:
            # Attempt to upload the data
            self._PostData = requests.post(self._GAIT_URL, json=self._GaitData)    
            # Check if the data was uploaded
            if not self._PostData.ok: 
               currAttempt += 1 
               self.webReqMessage.emit((-1, f"Gait Data Upload Failed, will attempt to send again in {self._timeBetweenSends} sec"))
               time.sleep(self._timeBetweenSends)
            else: 
                break 
            # If the data was not uploaded after this amount of max attempts then exit
            if currAttempt == self._uploadMaxAttempts: 
                self.webReqMessage.emit((-1, f"Error Unable to upload data to {self._GAIT_URL}!"))
                break;  



    def uploadGaitResults(self, ptInfo : tuple, dataDict : dict, gaitAvgSpd : float):
        
        # Clean The Name and ID 
        ptID, ptName = ptInfo
        
        # Lets Format the Data First 
        date = time.strftime('%Y-%m-%d')
        
        try:
           
            cleanDict = dict()
            for keyVal, dataVal in dataDict.items(): 
                if not keyVal in cleanDict:
                    cleanDict.update({keyVal: {'Program Run' : keyVal, 'Results' : []}})
                # Enumerate Through Lists of Dict
                for item in dataVal: 
                    # Insert the data into the results sectino of dictionary, but each element should be its own array
                    cleanDict[keyVal]['Results'].append(
                    {
                        'time': item['CurrTime'], 
                        'distance' : item['distance_Measure'], 
                        'velocity' : item['currVelocity']
                    }
                    )
                    
            
        except Exception as err: 
            print("There was an error\n\n")
            print(traceback.format_exc())
        
        self._GaitData = {
            'patientId' : str(ptID),
            'date' : date,
            'averageGaitSpeed': gaitAvgSpd,
            'gaitSpeedResults':cleanDict.values(),
            'PatientName' : str(ptName),

        }
        
        #print(f"\n {self._GaitData['gaitSpeedResults']} ")
            
        
        # Disabled for now 
        # Send the Data Now That We Have Prepared it
        #self.__sendGaitSpd()

     
        
    def __sendKyphosisIndex(self): 
        if self._KyphosisData is None: 
            self.webReqMessage.emit((-1, f"Error No Kyphosis Data To Upload!"))
            return
        
        currAttempt = 0 
        
        while True: 
            self._PostData = requests.post(self._Kyphosis_URL, json=self._GaitData)
            if not self._PostData.ok: 
                currAttempt += 1
                self.webReqMessage.emit((-1, f"Kyphosis Data Upload Failed, will attempt to send again in {self._timeBetweenSends} sec"))
                time.sleep(self._timeBetweenSends)
            else:
                break
            # Check if the attempts were exceeded
            if currAttempt == self._uploadMaxAttempts:
                self.webReqMessage.emit((-1, f"Error Unable to upload data to {self._Kyphosis_URL}!"))
    
    
    
    def uploadKyphosisResult(self, ptInfo: tuple, avgKypIndex : float): 
       
       ptID, ptName = ptInfo
       
       date1 = time.strftime('%Y-%m-%d')
       self._KyphosisData = {
           'patientId': ptID,
           'patientName' : ptName,
           'date': date1 ,  # Date must be in this format yyyy-mm-dd
           'kyphosisIndex': avgKypIndex,
       }
       
       print(f"Kyphosis Upload: {self._KyphosisData}")
       
       # Disable For Now
       # Now Actually Upload the Data to the Server
       #self.__sendKyphosisIndex()
    
    
    def logout(self): 
        try:
            requests.post(self._Logout_URL, cookies=self._Response.cookies)
            print("Logged Out")
        except Exception as err: 
            print(f"There was an error: {err}") 
            