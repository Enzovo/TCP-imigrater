from TCP_socket import TCP_Connection_Final
from threading import Thread
import socket, os
def send():
	if os.path.exists('test_1_send.log'):
		os.remove('test_1_send.log')
	tcp_sender = TCP_Connection_Final((socket.gethostname(), 5001), (socket.gethostname(), 5055), 578430997, 2356389583, log_file='test_1_send.log')
	line = b'blah'
	tcp_sender.send(bytes([i % 256 for i in range(600)]) , True)
def recv():
	other_addr = (socket.gethostname(), 5001)
	my_addr = (socket.gethostname(), 5055)
	my_ISN = 2356389583
	other_ISN = 578430997
	if os.path.exists('test_1_recv.log'):
		os.remove('test_1_recv.log')
	tcp_sender = TCP_Connection_Final(my_addr, other_addr,my_ISN , other_ISN, log_file='test_1_recv.log')
	got = tcp_sender.recv(1024)
	if got == bytes([i % 256 for i in range(600)]):
		print('Bytes match')

thread = Thread(target=recv)
thread.start()
# get_one()
send()
