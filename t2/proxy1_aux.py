import sys
import jsockets
import threading

CLOSED = 1
WAITING = 2
CONNECTED = 3
header_length = 2
max_clients = 10
TCP_status = [CLOSED] * max_clients
sock_list = [None] * max_clients



def UDP_rdr(sock_udp):
	global TCP_status, sock_list

	while True:
		try:
			data = sock_udp.recv(4096)
		except:
			data = None

		if not data:
			break

		data = data.decode()
		id = int(data[1])

		if TCP_status[id] == CLOSED:
			continue
		
		if TCP_status[id] == WAITING and data[0] == 'C':
			data = data[header_length:]

			if data != "OK":
				TCP_status[id] = CLOSED
				sock_list[id].close()
				continue

			TCP_status[id] = CONNECTED

		if TCP_status[id] == CONNECTED and data[0] == 'D':
			data = data[header_length:]
			sock_list[id].send(data.encode())

		if TCP_status[id] != CLOSED and data[0] == 'X':
			sock_list[id].close()
			TCP_status[id] = CLOSED


def TCP_rdr(sock_tcp, sock_udp, id_socket):
	global TCP_status, sock_list

	while True:
		try:
			data = sock_tcp.recv(MAX_DATA)
		except:
			data = None

		if not data:
			break

		data = data.decode()
		sock_udp.send((f"D{id_socket}" + data).encode())

	print(f"Desconectado el cliente {5}")
	sock_tcp.close()
	TCP_status[0] = CLOSED
	sock_udp.send(f"X{0}".encode())


def proxy(sock_tcp, sock_udp):
	global TCP_status, sock_list

	id = -1
	for i in range(max_clients):
		if TCP_status[i] == CLOSED:
			id = i
			break
	if id == -1:
		sock_tcp.close()
		return

	TCP_status[id] = WAITING
	sock_list[id] = sock_tcp

	print(f"Conectado el cliente {id}")

	sock_udp.send(f"C{id}0".encode())
	TCP_rdr(sock_tcp, sock_udp, id)

# -----------MAIN------------

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

t = threading.Thread(target=UDP_rdr, args=(sock_udp,))
t.start()

while True:
	sock_tcp, addr = s.accept()
	t = threading.Thread(target=proxy, args=(sock_tcp, sock_udp))
	t.start()