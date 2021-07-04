#!/usr/bin/python3
# proxy2  multi-clientes compartiendo sockets con REUSEPORT 
# ./proxy2 udp-in host port
# Usando threads
import os, signal
import sys
import socket, jsockets
import threading
import struct

MAX_DATA = 1500

def UDP_rdr(conn2, conn, data):

    while True:
        if data:
            print('UDP_rdr Recibi:')
            print(data)
            # Acabo de leer una serie de bytes desde UDP
            try:
                conn.send(data)
            except:
                break
        try:
            data=bytearray(conn2.recv(MAX_DATA))
        except:
            data=None
        if not data:
            break
    conn.close()  # Para matar TCP_rdr y al server

def TCP_rdr(conn, conn2):

    while True:
        try:
            data=bytearray(conn.recv(MAX_DATA))
        except:
            data=None
        print('TCP_rdr Recibi:')
        print(data)
        # Acabo de leer una serie de bytes desde TCP
        if not data:
            break
        conn2.send(data)

    print('TCP_rdr Exit()')
    conn.close()

# Este el servidor de un socket ya conectado
# y el cliente del verdadero servidor (TCP_sock, UDP_sock)
def proxy(conn, addr, data, host, portout):

    conn2 = jsockets.socket_tcp_connect(host, portout)
    if conn2 is None:
        print('conexión rechazada por '+host+', '+portout)
        sys.exit(1)

    conn.connect(addr)
    # timeout de 100s, para que muera sin tráfico
    conn.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, struct.pack("LL",100,0))
    print('Nueva conexión UDP')

    # inicializar el mundo
    newthread1 = threading.Thread(target=UDP_rdr, daemon=True, args=(conn, conn2, data))
    newthread1.start()
    TCP_rdr(conn2, conn)
    print('TCP rdr retorna, esperando UDP_rdr...')
    newthread1.join()
    conn2.close()
    print('Cliente desconectado')


# Main
if len(sys.argv) != 4:
    print('Use: '+sys.argv[0]+' port-in host port-out')
    sys.exit(1)

udpportin = sys.argv[1]
host = sys.argv[2]
portout = sys.argv[3]

s = jsockets.socket_udp_bind(udpportin)
if s is None:
    print('bind falló')
    sys.exit(1)

while True:
    data, addr = s.recvfrom(MAX_DATA)
    if not data: break
    conn = jsockets.socket_udp_bind(udpportin)
    if conn is None:
        print('2nd socket failed')
        sys.exit(1)

    pid = os.fork()
    if pid == 0:
        s.close()
        proxy(conn, addr, data, host, portout)
        sys.exit(0)
    else:
        conn.close()
