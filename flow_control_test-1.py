from TCP_socket import TCP_Connection_Final
from threading import Thread
import socket, os
from time import sleep
def send():
	if os.path.exists('test_3_send.log'):
		os.remove('test_3_send.log')
	tcp_sender = TCP_Connection_Final((socket.gethostname(), 5003), (socket.gethostname(), 5060), 578430997, 2356389583, log_file='test_3_send.log')
	line = b'blah'
	file = bytes([i % 256 for i in range(10000)])
	done = False
	while not done:
		if len(file) > 1000:
			to_send = file[:1000]
			file = file[1000:]
		else:
			to_send = file
			done = True
		print(tcp_sender.send(to_send, done))
def recv():
	other_addr = (socket.gethostname(), 5003)
	my_addr = (socket.gethostname(), 5060)
	my_ISN = 2356389583
	other_ISN = 578430997
	if os.path.exists('test_3_recv.log'):
		os.remove('test_3_recv.log')
	tcp_sender = TCP_Connection_Final(my_addr, other_addr,my_ISN , other_ISN, log_file='test_3_recv.log')
	for x in range(20):
		sleep(0.5)
		if x == 9:
			bad_packet = b'\x13\xbf\x13\x89\x8cs\xa6\xcf"z/\xe5P\x10\x180\x00\x00\x00\x00'
			tcp_sender.sock.sendto(bad_packet, tcp_sender.dest)
		tcp_sender._main_loop()
	got = b''
	while len(got) < 10000:
		print(f'getting data, have {len(got)}')
		got += tcp_sender.recv(1024)
	if got == bytes([i % 256 for i in range(10000)]):
		print('Bytes match')

thread = Thread(target=recv)
thread.start()
# get_one()
send()
