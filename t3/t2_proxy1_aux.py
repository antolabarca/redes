import sys
import jsockets
import threading
from jsockets import send_loss, recv_loss
import queue

CLOSED = 1
WAITING = 2
CONNECTED = 3
header_length = 3
max_clients = 10
TCP_status = [CLOSED] * max_clients
sock_list = [None] * max_clients
TCP_queues = [None] * max_clients
ACK_seqnum = [0] * max_clients
Timeout = 10
LOSS_RATE = 0

def UDP_rdr(sock_udp):
	global TCP_status, sock_list, TCP_queues, ACK_seqnum, LOSS_RATE

	while True:
		try:
			print("[UDP_rdr] Recibiendo")
			data = sock_udp.recv(4096)
		except:
			data = None

		if not data:
			break

		print(f"[UDP_rdr] Recibido {data}")
		data = data.decode()
		id = int(data[1])

		if TCP_status[id] == CLOSED:
			print(f"[UDP_rdr] Socket TCP {id} cerrado")
			continue
		
		if TCP_status[id] == WAITING and data[0] == 'C':
			TCP_queues[id].put(data)

		if TCP_status[id] == CONNECTED and data[0] == 'D':
			print(f"[UDP_rdr] Enviando ACK")
			send_loss(sock_udp, LOSS_RATE, f"A{id}{data[2]}".encode())

			if str(ACK_seqnum[id]) == data[2]:
				print(f"[UDP_rdr] Seqnum correcto")
				ACK_seqnum[id] = (ACK_seqnum[id] + 1) % 2
				data = data[header_length:]
				sock_list[id].send(data.encode())
			else:
				print(f"[UDP_rdr] SeqNum incorrecto")
				continue

		if TCP_status[id] != CLOSED and data[0] == 'X':
			TCP_queues[id].put(data)
			TCP_status[id] = CLOSED

		if TCP_status[id] == CONNECTED and data[0] == 'A':
			TCP_queues[id].put(data)


def TCP_rdr(sock_tcp, sock_udp, id):
	global TCP_status, sock_list, TCP_queues, LOSS_RATE

	try:
		ack = TCP_queues[id].get(timeout=Timeout)
	except queue.Empty:
		ack = None

	if ack and ack[0] == 'C':
		print(f"[TCP_rdr] ACK Connect: {ack}")
		ack = ack[header_length:]
		if ack != "OK":
			print(f"[TCP_rdr] Conexión {id} rechazada")
			TCP_status[id] = CLOSED
			sock_list[id].close()
			return
		else:
			TCP_status[id] = CONNECTED
			print(f"[TCP_rdr] Conexión {id} aceptada")
	else:
		print(f"[TCP_rdr] Conexión {id} timeout")
		TCP_alive[id] = CLOSED
		sock_list[id].close()
		return

	seqnum = 0
	finished = False

	while not finished:
		try:
			print(f"[TCP_rdr, {id}] Recibiendo")
			data = sock_tcp.recv(4096)
		except:
			data = None

		if not data:
			break

		print(f"[TCP_rdr, {id}] Recibido {data}")
		data = data.decode()

		while True:
			send_loss(sock_udp, LOSS_RATE, f"D{id}{seqnum}{data}".encode())
			try:
				ack = TCP_queues[id].get(timeout=Timeout)
			except queue.Empty:
				ack = None

			if ack:
				if ack[0] == 'X':
					print(f"[TCP_rdr, {id}] Desconectado")
					finished = True
					break
				if ack[0] != 'A' or ack[1] != str(id) or ack[2] != str(seqnum):
					print(f"[TCP_rdr, {id}] Reintentando (ACK erróneo)")
					continue
				else:
					seqnum = (seqnum + 1) % 2
					break
			else:
				print(f"[TCP_rdr, {id}] Reintentando (no hubo ACK)")
				continue

	sock_tcp.close()
	TCP_status[id] = CLOSED
	send_loss(sock_udp, LOSS_RATE, f"X{id}{seqnum}".encode())
	print(f"[TCP_rdr, {id}] Enviado X{id}{seqnum}")



def proxy(sock_tcp, sock_udp):
	global TCP_status, sock_list, TCP_queues, ACK_seqnum, LOSS_RATE

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
	TCP_queues[id] = queue.Queue()
	ACK_seqnum[id] = 0

	print(f"Conectado el cliente {id}")

	send_loss(sock_udp, LOSS_RATE, f"C{id}{0}".encode())
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