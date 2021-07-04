#!/usr/bin/python3
# proxy1 in-port host out-port
# mono-cliente
# simula TCP sobre un UDP con proxy2
# Usa threads (uno TCP->UDP y otro UDP->TCP) y espera al siguiente cliente cuando uno termina
import os, signal
import sys
import socket, jsockets
import threading
import struct, time

MAX_DATA = 1500
TCP_alive = [False for _ in range(10)]
THREADS = [0]*10
client_conns = [0]*10
closed = True
change = [False for _ in range(10)]
ans = [0 for _ in range(10)]  # 0 no ha pasado nada, 1 se acepto la conexion, -1 se rechazo

ID = [False for _ in range(10)]   # los valores de ID ocupados, inicialmente todos libres

def UDP_rdr(conn2):  # uno
    global TCP_alive
    global client_conns
    global closed
    global ans

    while closed:
        time.sleep(0.05)
    print("a no mimir")
    
    while True:
        try:
            data=bytearray(conn2.recv(MAX_DATA))  # los datos recibidos desde conn2, que es el udp
        except:
            data=None

        if data is not None:
            data_deco = data.decode()
            code = data_deco[0]
            client_id = data_deco[1]
            msg = data_deco[2:]

            if code == "C":
                if msg == "OK":
                    print("ok")
                    ans[int(client_id)] = 1
                else:
                    print("nok")
                    ans[int(client_id)] = -1      

        if not data  and True not in TCP_alive:
            print("break de udp")
            break
        if data and code=="D":
            print('UDP_rdr Recibi:')
            print(data)
            # Acabo de leer una serie de bytes desde UDP
            try:
                conn = client_conns[int(client_id)]
                conn.send(msg.encode())  # se mandan los datos por la conexion conn, a client echo
            except:
                break

def TCP_rdr(conn, conn2, client_id):  # varios
    global TCP_alive
    global THREADS
    global closed
    global ans

    TCP_alive[client_id] = True
    first_time = True
    while True:
        try:
            data=bytearray(conn.recv(MAX_DATA))
        except:
            data=None
        print('TCP_rdr Recibi:')
        print(data)
        # Acabo de leer una serie de bytes desde TCP
        if not data:
            print("no hay datos por el socket tcp")
            b = bytearray(("X"+str(client_id)).encode())
            conn2.send(b)
            break
        if first_time:
            b = bytearray(("C"+str(client_id)).encode())
            conn2.send(b)
            time.sleep(0.01)  # Le doy tiempo a proxy2 para que se "conecte" conmigo o se confunde con muchos paquetes
            closed = False
            while ans[int(client_id)]==0:
                time.sleep(0.01)
            if ans[int(client_id)]==1:
                print("conexion aceptada")
            else:
                print("error de conexion")
            ans[int(client_id)]=0
     
            first_time = False
        data = bytearray(("D"+str(client_id)).encode()) + data
        conn2.send(data)
        print("data enviada:")
        print(data)

    print('TCP_rdr Exit()')
    conn.close()
    b = bytearray(("X"+str(client_id)).encode())
    conn2.send(b)
    TCP_alive[client_id] = False

# Este el servidor de un socket
# y el cliente del verdadero servidor (TCP_sock, UDP_sock)
def proxy(conn, conn2, client_id):  
    global THREADS
    global ID
    global client_conns

    
    TCP_rdr(conn, conn2, client_id)
    print('TCP rdr retorna, esperando UDP_rdr...')
    ID[client_id] = False
    client_conns[client_id] = 0
    print('Cliente desconectado')
    change[client_id] = True

# Main

if len(sys.argv) != 4:
    print('Use: '+sys.argv[0]+' port-in host port-out')
    sys.exit(1)

portin = sys.argv[1]
host = sys.argv[2]
portout = sys.argv[3]

conn2 = jsockets.socket_udp_connect(host, portout)
if conn2 is None:
    print('conexión UDP rechazada por '+host+', '+portout)
    sys.exit(1)


# timeout de 1s, para que retorne siempre y vea si hay cliente aun...
conn2.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, struct.pack("LL",1,0))

# inicializar el mundo
newthread1 = threading.Thread(target=UDP_rdr, daemon=True, args=(conn2,))   #udp -> 1 thread
newthread1.start()


while True:

    s = jsockets.socket_tcp_bind(portin)
    conn, addr = s.accept()
    client_id = ID.index(False)
    ID[client_id] = True

    if THREADS[client_id] != 0:
        THREADS[client_id].join()  # se mata el thread que había antes de hacer uno nuevo

    client_conns[client_id] = conn
    print("client id es:")
    print(client_id)

    if s is None:
        print('bind falló')
        sys.exit(1)
    print('Aceptando cliente')
    
    newthread = threading.Thread(target=proxy, daemon=True, args=(conn, conn2, client_id))
    newthread.start()
    THREADS[client_id] = newthread



newthread1.join()