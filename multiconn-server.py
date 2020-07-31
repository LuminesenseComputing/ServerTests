import sys
import socket
import selectors
import types
import time

sel = selectors.DefaultSelector()

class lightModule:
    def __init__(self, port):
        self.state = 0 #0 is off, 1 is on, 2 is turning off, 3 is turning on
        self.port = port
        self.changeTime = 0
        print("    Light ", self.port, " is now ONLINE.")

   #EDGE CASES TO TAKE CARE OF:
   #trying to turn light on or off while it is in unknown state
   #time.time goes past the max value and goes back to zero
   #OTHER FIXES:
   #instead of change state make it more precise control... ie option to turn on/off

    def changeState(self):#must add "turning on/off" states
        if self.state == 0:
            #self.state = 1
            self.state = 3
            print("    Light ", self.port, " is now TURNING ON.")
        elif self.state == 1:
            #self.state = 0
            self.state = 2
            print("    Light ", self.port, " is now TURNING OFF.")
        self.changeTime = time.time()

    def confirmStateChange(self):
        self.changeTime = time.time()#reset the time at which the state change was last attempted
        if self.state == 3:
            print("    Light ", self.port, "turning on confirmation requested.")
        elif self.state == 2:
            print("    Light ", self.port, "turning off confirmation requested.")

    def finalizeChangeState(self):
        if self.state == 3:
            #self.state = 1
            self.state = 1
            print("    Light ", self.port, " is now ON.")
        elif self.state == 2:
            #self.state = 0
            self.state = 0
            print("    Light ", self.port, " is now OFF.")

    def closeLight(self):
        print("    Light ", self.port, "is now OFFLINE.")

def accept_wrapper(sock, lightModuleDict):
    conn, addr = sock.accept()  # Should be ready to read
    print("accepted connection from", addr)
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b"", messages=[], outb=b"")
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)
    lightModuleDict[addr[1]] = lightModule(addr[1])

def service_connection(key, mask, lightModuleDict, changeState):
    sock = key.fileobj
    data = key.data
    lightModule = lightModuleDict[data.addr[1]]
    if changeState == True: #really sketch. Just demonstrating ideas
        data.messages  += [b"CHANGE STATE"]
        lightModule.changeState()

    #check if any messages have been received from the light module
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Should be ready to read
        if recv_data:
            print("received",repr(recv_data), "from", data.addr)
            if recv_data == b"TURNED ON" or recv_data == b"TURNED OFF":#confirmation that the light has turned on/off
                lightModule.finalizeChangeState()
                #data.outb += recv_data
            if recv_data == b"CONFIRMED ON" or recv_data == b"CONFIRMED OFF":#confirmation that the light has turned on/off after a delayed response
                lightModule.finalizeChangeState()
        else:
            lightModule.closeLight()
            lightModuleDict.pop(data.addr[1])
            print("closing connection to", data.addr)
            sel.unregister(sock)
            sock.close()

    #if the current light has passed 2 seconds since attempting to turn on/off without response, confirm status
    if not data.messages: #must check to make sure the light was not just turned on or off
        if lightModule.state == 3 and (time.time() - lightModule.changeTime) > 2:
            data.messages += [b"CONFIRM ON"]
            lightModule.confirmStateChange()
        elif lightModule.state == 2 and (time.time() - lightModule.changeTime) > 2:
            data.messages += [b"CONFIRM OFF"]
            lightModule.confirmStateChange()

    #send any waiting messages to the light module
    if mask & selectors.EVENT_WRITE:
        if not data.outb and data.messages:
            data.outb = data.messages.pop()
        if data.outb:
            print("Sending", repr(data.outb), "to", data.addr)
            sent = sock.send(data.outb)  # Should be ready to write
            data.outb = data.outb[sent:]


if len(sys.argv) != 1:
    print("usage:", sys.argv[0], "no input arguments")
    sys.exit(1)

host = "192.168.4.1"
port = 50007
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lsock.bind((host, port))
lsock.listen()
print("listening on", (host, port))
lsock.setblocking(False)

sel.register(lsock, selectors.EVENT_READ, data=None)


try:
    lightModuleDict = {}
    changeState = False
    startTime = time.time()
    while True:
        if time.time() - startTime > 7:
            changeState = True
            startTime = time.time()
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None:
                accept_wrapper(key.fileobj, lightModuleDict)
            else:
                service_connection(key, mask, lightModuleDict, changeState)
        changeState = False
except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")
finally:
    sel.close()
