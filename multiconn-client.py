import sys
import socket
import selectors
import types

sel = selectors.DefaultSelector()
#messages = [b"Message 1 from client.", b"Message 2 from client."]


###################
#REMEMBER TO CONNECT TO WIFI
####################

class lightModuleClient:
    def __init__(self, connid):
        self.state = 0 #0 is off, 1 is on
        self.connid = connid
        print("    Light ", self.connid, " is now ONLINE.")

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


def start_connections(host, port, num_conns, lightModuleDict):
    server_addr = (host, port)
    for i in range(0, num_conns):
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
        sel.register(sock, events, data=data)
        lightModuleDict[connid] = lightModuleClient(connid)

def service_connection(key, mask, lightModuleDict):
    sock = key.fileobj
    data = key.data
    lightModule = lightModuleDict[data.connid]
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Should be ready to read
        if recv_data:
            print("received", repr(recv_data), "from connection", data.connid)
            #data.recv_total += len(recv_data)
            if (recv_data == b"CHANGE STATE"):
                #turn the light on or off
                lightModule.changeState()
                if lightModule.state == 0:
                    #data.messages += [b"TURNED OFF"]
                    pass
                else:
                    pass
                    #data.messages += [b"TURNED ON"]
            if (recv_data == b"CONFIRM ON"):
                lightModule.confirmOn()
                data.messages += [b"CONFIRMED ON"]
            if (recv_data == b"CONFIRM OFF"):
                lightModule.confirmOff()
                data.messages += [b"CONFIRMED OFF"]

        if not recv_data: #or data.recv_total == data.msg_total:
            print("closing connection", data.connid)
            sel.unregister(sock)
            sock.close()
            lightModule.closeLight()
            lightModuleDict.pop(connid)
    
    if mask & selectors.EVENT_WRITE:
        if not data.outb and data.messages:
            data.outb = data.messages.pop(0)
        if data.outb:
            print("sending", repr(data.outb), "to connection", data.connid)
            sent = sock.send(data.outb)  # Should be ready to write
            data.outb = data.outb[sent:]


if len(sys.argv) != 2:
    print("usage:", sys.argv[0], "<num_connections>")
    sys.exit(1)

lightModuleDictGlobal = {}
num_conns = sys.argv[-1]
host = "192.168.4.1"
port = "50007"
start_connections(host, int(port), int(num_conns), lightModuleDictGlobal)

try:
    while True:
        events = sel.select(timeout=1)
        if events:
            for key, mask in events:
                service_connection(key, mask, lightModuleDictGlobal)
        # Check for a socket being monitored to continue.
        if not sel.get_map():
            break
except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")
finally:
    sel.close()