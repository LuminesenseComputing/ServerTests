import multiconnClientClass2
import selectors

sel = selectors.DefaultSelector()

#initialStateList is in the format [[initial actualState, actualName, actualCurrentTime], ... repeated for each light on this light module]
initialStateList = [["OFF", "lightName", 0]]

wifiComm = multiconnClientClass2.wifiCommunicator(sel, initialStateList)

wifiState = None

while True:
    wifiComm.checkWifi()#check wifi signals
    #now can check wifiComm.lightModuleDict to see what the wifi is instructing the light to do
    #print(wifiComm.getState())
    wifiState = wifiComm.getState() #format [connectionStatus, wifiState, wifiName]
    #print(wifiState)
    actualLightState = [wifiState[1], "lightName", None, None] # format ["ON", nameOfLight, currentTime, triggeredOFF]
    wifiComm.confirmState(actualLightState)
sel.close()