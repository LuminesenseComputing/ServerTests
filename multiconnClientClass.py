import sys
import socket
import selectors
import types


class lightModuleClient:
    def __init__(self, connid):
        self.state = 2 #0 is off, 1 is on, 2 is disconnected
        self.connid = connid
        self.name = "light"
        print("    Light ", self.connid, " is NOT CONNECTED.")

    def connect(self):#light becoming connected
        self.state = 0 #start in the off state once connected
        print("    Light ", self.connid, " is now CONNECTED AND OFF.")

    def changeName(self, newName):#change of name has been requested
        self.name = newName

    def confirmNameChange(self, newName):
        #not yet implemented... to be something along the lines of self.name == wifiCommunicator.actualLightState[Name]
        pass

    def changeState(self):#change state of the light
        if self.state == 0:
            self.state = 1
            print("    Light ", self.connid, " is now ON.")
        else:
            self.state = 0
            print("    Light ", self.connid, " is now OFF.")

    #yet to be properly implemented using the self.actualLightState variable in the wifiCommunicator class
    def confirmOn(self):#if the server is making sure that the light is on, ensure the light is on
        self.state = 1
        print("    Light ", self.connid, " is now CONFIRMED ON.")

    #yet to be properly implemented using the self.actualLightState variable in the wifiCommunicator class
    def confirmOff(self):#if the server is making sure that the light is off, ensure the light is off
        self.state = 0
        print("    Light ", self.connid, " is now CONFIRMED OFF.")
        
    def closeLight(self):
        print("    Light ", self.connid, "is now OFFLINE.")


class wifiCommunicator():

    def __init__(self, selector, num_conns=3):
        self.sel = selector
        self.lightModuleDict = {}
        self.num_conns = num_conns
        self.host = "192.168.4.1"
        self.port = int("50007")
        self.start_connections()
        self.actualLightState = None

    def start_connections(self):
        server_addr = (self.host, self.port)
        for i in range(0, self.num_conns):
            connid = i + 1
            print("starting connection", connid, "to", server_addr)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setblocking(False)
            sock.connect_ex(server_addr)
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
            data = types.SimpleNamespace(
                connid=connid,
                #msg_total=sum(len(m) for m in messages),
                #recv_total=0,
                messages=[],#list(messages),
                outb=b"",
            )
            self.sel.register(sock, events, data=data)
            self.lightModuleDict[connid] = lightModuleClient(data.connid)

    def service_connection(self, key, mask):
        sock = key.fileobj
        data = key.data
        lightModule = self.lightModuleDict[data.connid]
        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(1024)  # Should be ready to read
            if recv_data:
                print("received", repr(recv_data), "from connection", data.connid)
                #data.recv_total += len(recv_data)
                if (recv_data == b"CHANGE STATE"):
                    #turn the light on or off
                    lightModule.changeState()
                    if lightModule.state == 0:
                        data.messages += [b"TURNED OFF"]
                    else:
                        data.messages += [b"TURNED ON"]
                if (recv_data == b"CONFIRM ON"):
                    lightModule.confirmOn()
                    data.messages += [b"CONFIRMED ON"]
                if (recv_data == b"CONFIRM OFF"):
                    lightModule.confirmOff()
                    data.messages += [b"CONFIRMED OFF"]
                if (recv_data == b"CONNECTED"):
                    lightModule.connect()
                if (recv_data[0:7] == b"CHANGEN"):#full command is CHANGENAME_newName
                    lightModule.changeName(recv_data[11:])#set the name of the light to the name in the wifi message
                if (recv_data[0:11]==b'CONFIRMNAME'):#full command is CONFIRMCHANGENAME_newName
                    if lightModule.confirmNameChange(recv_data[17:]) == 0:#check whether the light name has been changed
                        data.messages += [b"NOTCHANGED"]#confirm that the name has not been changed
                    else:
                        data.messages += [b"CHANGED"]#confirm that the name has been changed
            if not recv_data: #or data.recv_total == data.msg_total:
                print("closing connection", data.connid)
                self.sel.unregister(sock)
                sock.close()
                lightModule.closeLight()
                self.lightModuleDict.pop(connid)
        
        if mask & selectors.EVENT_WRITE:
            if not data.outb and data.messages:
                data.outb = data.messages.pop(0)
            if data.outb:
                print("sending", repr(data.outb), "to connection", data.connid)
                sent = sock.send(data.outb)  # Should be ready to write
                data.outb = data.outb[sent:]
    '''
    This function returns the state of the light wifi command in the light dict with the highest connID on this pi0
    (obviously there would be usually only 1 light module for a given pi0... but this format is useful for testing)

    Outputs:
        - None if there are no light modules initialized
        - State if there is a light module, in this format: ["CONNECTED", "OFF", nameOfLight], ["DISCONNECTED", "OFF", nameOfLight], or ["CONNECTED", "ON", nameOfLight]
        where nameOfLight is the name which the wifi is requesting that the lightModuleBeNamed

    Note that we have not dealt with the edge case of the piui disconnecting... ie ["DISCONNECTED", "ON"]
    ''' 
    def getState(self):
        state = None
        highestConnID = -1
        for id in self.lightModuleDict:#iterate through each light module on this pi0 
            if id > highestConnID: #if we have found a light with a new higher connid than previously... update the state with info for this light
                lightModule = self.lightModuleDict[id]
                if lightModule.state == 2:
                    state = ["DISCONNECTED", "OFF", lightModule.name]
                elif lightModule.state == 1:
                    state = ["CONNECTED", "ON", lightModule.name]
                elif lightModule.state == 0:
                    state = ["CONNECTED", "OFF", lightModule.name]
        return state
    
    '''
    Tells the wifiCommunicator class about the actual state of the light

    The wifi's response to this has not yet been implemented.

    Input argument: Can be one of ["ON", nameOfLight, currentTime, triggeredOFF]
    where nameOfLight is the name of the light, currentTime is the currentTime the light has been on for, and 
    triggeredOFF is boolean whether the motion sensor has been triggered
    '''
    def confirmState(self, actualLightState):
        self.actualLightState = actualLightState

    def checkWifi(self):
        try:
            events = self.sel.select(timeout=1)
            if events:
                for key, mask in events:
                    self.service_connection(key, mask)
            # Check for a socket being monitored to continue.
            if not self.sel.get_map():
                return
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")
