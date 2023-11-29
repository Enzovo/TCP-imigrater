from TCP_socket import TCP_Connection_Final
from threading import Thread
import socket, os
from time import sleep
def send():
	if os.path.exists('test_2_send.log'):
		os.remove('test_2_send.log')
	tcp_sender = TCP_Connection_Final((socket.gethostname(), 5004), (socket.gethostname(), 5061), 578430997, 2356389583, log_file='test_2_send.log')
	line = b'blah'
	tcp_sender.send(bytes([i % 256 for i in range(600)]) , True)
def recv():
	other_addr = (socket.gethostname(), 5004)
	my_addr = (socket.gethostname(), 5061)
	my_ISN = 2356389583
	other_ISN = 578430997
	if os.path.exists('test_2_recv.log'):
		os.remove('test_2_recv.log')
	tcp_sender = TCP_Connection_Final(my_addr, other_addr,my_ISN , other_ISN, log_file='test_2_recv.log')
	sleep(20)
	got = tcp_sender.recv(1024)
	if got == bytes([i % 256 for i in range(600)]):
		print('Bytes match')

thread = Thread(target=recv)
thread.start()
# get_one()
send()
