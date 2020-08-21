import multiconnClientClass
import selectors

sel = selectors.DefaultSelector()

wifiComm = multiconnClientClass.wifiCommunicator(sel, num_conns=5)

while True:
    wifiComm.checkWifi()#check wifi signals
    #now can check wifiComm.lightModuleDict to see what the wifi is instructing the light to do

sel.close()