#!/usr/bin/python3
# Echo client program
# Version con dos threads: uno lee de stdin hacia el socket y el otro al revés
import jsockets
import sys, threading
import time

Eof = '---EOFEO---'
Eof1 = '1--EOFEO---'
Eof2 = '2--EOFEO---'

def Rdr(s):
    # s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, struct.pack("LL",10,0))
    while True:
        try:
            data=s.recv(1500).decode()
        except:
            data = None
        if not data or data[-len(Eof):] == Eof or data[-len(Eof):] == Eof1 or data[-len(Eof):] == Eof2:
            if data:
                print(data[:-len(Eof)], end = '')
            break
        print(data, end = '')

if len(sys.argv) != 3:
    print('Use: '+sys.argv[0]+' host port')
    sys.exit(1)

s = jsockets.socket_tcp_connect(sys.argv[1], sys.argv[2])
if s is None:
    print('could not open socket')
    sys.exit(1)

# Creo thread que lee desde el socket hacia stdout:
newthread = threading.Thread(target=Rdr, args=(s,))
newthread.start()

# En este otro thread leo desde stdin hacia socket:
for line in sys.stdin:
    s.send(line.encode())

s.send(Eof.encode())
