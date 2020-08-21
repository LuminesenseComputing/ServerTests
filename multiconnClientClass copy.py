import sys
import socket
import selectors
import types


class lightModuleClient:
    def __init__(self, connid):
        self.state = 0 #0 is off, 1 is on
        self.connid = connid
        print("    Light ", self.connid, " is now .")

    def changeState(self):#change state of the light
        if self.state == 0:
            self.state = 1
            print("    Light ", self.connid, " is now ON.")
        else:
            self.state = 0
            print("    Light ", self.connid, " is now OFF.")

    def confirmOn(self):#if the server is making sure that the light is on, ensure the light is on
        self.state = 1
        print("    Light ", self.connid, " is now CONFIRMED ON.")
    
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
            self.lightModuleDict[connid] = lightModuleClient(connid)

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
