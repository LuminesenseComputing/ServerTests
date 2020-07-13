import sys
import socket
import selectors
import types
import time

sel = selectors.DefaultSelector()

class lightModule:
    def __init__(self, port):
        self.state = 0 #0 is off, 1 is on
        self.port = port
        print("    Light ", self.port, " is now ONLINE.")

    def changeState(self):#must add "turning on/off" states
        if self.state == 0:
            self.state = 1
            print("    Light ", self.port, " is now ON.")
        else:
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
    if changeState == True: #really sketch. Just demonstrating ideas
        data.messages  += [b"CHANGE STATE"]
        lightModuleDict[data.addr[1]].changeState()
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Should be ready to read
        if recv_data:
            #data.outb += recv_data
            pass
        else:
            lightModuleDict[data.addr[1]].closeLight()
            lightModuleDict.pop(data.addr[1])
            print("closing connection to", data.addr)
            sel.unregister(sock)
            sock.close()

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
        if time.time() - startTime > 5:
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
