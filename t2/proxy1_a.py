import sys
import jsockets
import threading
import time
import queue

# fuertemente basado en el codigo del aux, con un poquito de mi codigo de la t1

CLOSED = 1
WAITING = 2
CONNECTED = 3
MAX_DATA = 1024
MAX_WIN = -1 # especificar un numero mayor a 0 para que tenga tamaño max
header_length = 3
max_clients = 10
timeout = 10
TCP_status = [CLOSED] * max_clients
sock_list = [None] * max_clients
id_pckg = 0 # para ir cambiando entre 0 y 1 dependiendo de cual toca
id_pckg_r = 0
acks = [False]*2 # si ya llego el ack del pckg
queue = queue.Queue(MAX_WIN) #]*10 # almacena colas para cada envío


# lee del socket udp, es solo uno
def UDP_rdr(sock_udp):
    global TCP_status, sock_list, acks, id_pckg_r
    
    while True:

        try:
            data = sock_udp.recv(MAX_DATA)
            #data = jsockets.recv_loss(sock_udp, 0, MAX_DATA)
        except:
            data = None
            
        if not data:
            continue

        print("Data recibida desde UDP:")
        data = data.decode()
        print(data)
        code = data[0]
        id_socket = int(data[1])
        id_pckg_a = int(data[2])
       

        if code=='C': # and TCP_status[id_socket] == WAITING :
            status = data[header_length:]
            
            if status != "OK":
                TCP_status[id_socket] = CLOSED
                sock_list[id_socket].close()
                continue
            
            TCP_status[id_socket] = CONNECTED
            
        if code == 'A': # and TCP_status[id_socket] == CONNECTED:
            # se recibio un ack, se debe marcar el ack correspondiente
            acks[id_pckg_a] = True


        if code == 'D' and TCP_status[id_socket] == CONNECTED:
            if id_pckg_a == id_pckg_r:  # si el pckg que llega es el que se espera
                msg = data[header_length:]
                sock_list[id_socket].send(msg.encode())
                id_pckg_r = 1 - id_pckg_r

            ack = ("A" + str(id_socket) + str(id_pckg_a)).encode()
            print("enviando ack")
            print(ack)    
            sock_udp.send(ack)
            #jsockets.send_loss(sock_udp, 50, ack)

            
        if code == 'X' and TCP_status[id_socket] != CLOSED:
            sock_list[id_socket].close()
            sock_list[id_socket] = None
            TCP_status[id_socket] = CLOSED

        if TCP_status[id_socket] == CLOSED:
            continue 
    
    print("chao ")


# lee de un socket tcp, el del numero id_socket
def TCP_rdr(sock_tcp, sock_udp, id_socket):
    global TCP_status, sock_list, queue
    
    while True:
        try:
            data = sock_tcp.recv(MAX_DATA)
        except:
            data = None
            
        if not data:
            break

        print(f"Se recibe data del socket {id_socket}:")
        print(data)
        
        data = data.decode()
        pckg = [id_socket, data]
        queue.put_nowait(pckg)

    print(f"Desconectado el cliente {id_socket}")
    sock_tcp.close()
    TCP_status[id_socket] = CLOSED

    msg = "X" + str(id_socket) + "0"
    sock_udp.send(msg.encode())


def send_stopandwait(sock_udp):
    global acks, sock_list, queue, id_pckg

    while True:

        if queue.empty():  # si no hay mensajes en la cola, esperar a que haya
            continue

        pckg = queue.get_nowait()
        id_socket = pckg[0]
        msg = pckg[1]

        if TCP_status[id_socket] == CLOSED:
            continue
        
        accepted = False
        data = ("D"+str(id_socket)+str(id_pckg)+msg).encode()

        print("Enviando datos: ")
        print(data)

        while not accepted:
            sock_udp.send(data)
            #jsockets.send_loss(sock_udp, 50,data)
            print("intento de envío")

            # se esperan 10 s (de a poquito para ir revisando si se acepto)
            for i in range(timeout*100):
                time.sleep(0.01)
                if acks[id_pckg]:
                    accepted = True
                    acks[id_pckg] = False
                    break

        print("paquete enviado correctamente")
        id_pckg = 1 - id_pckg


def proxy(sock_tcp, sock_udp):
    global TCP_status, sock_list, queues

    print("inicio proxy")
    
    if CLOSED not in TCP_status:
        sock_tcp.close()
        return 
        
    id_socket = TCP_status.index(CLOSED)
    
    TCP_status[id_socket] = WAITING
    sock_list[id_socket] = sock_tcp

    print(f"Conectado el cliente {id_socket}")
    data = f"C{id_socket}0"
    print("enviando "+data+" via socket udp")
    sock_udp.send(data.encode())

    TCP_rdr(sock_tcp, sock_udp, id_socket)

    
# ------------- MAIN --------------

if len(sys.argv) != 4:
    print('Use: '+sys.argv[0]+' port-in host port-out')
    sys.exit(1)

portin = sys.argv[1]
host = sys.argv[2]
portout = sys.argv[3]

s = jsockets.socket_tcp_bind(portin)
if s is None:
    print('bind falló')
    sys.exit(1)

sock_udp = jsockets.socket_udp_connect(host, portout)
if sock_udp is None:
    print('conexión UDP rechazada por '+host+', '+portout)
    sys.exit(1)

t0 = threading.Thread(target=UDP_rdr, args=(sock_udp,))
t0.start()

t1 = threading.Thread(target=send_stopandwait, args=(sock_udp,))
t1.start()


while True:
	sock_tcp, addr = s.accept()
	t = threading.Thread(target=proxy, args=(sock_tcp, sock_udp))
	t.start()


