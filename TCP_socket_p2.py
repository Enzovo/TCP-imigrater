from header_maker import *
import socket
import time
import select
from collections import deque
import os
# log_file = 'all_packets.log'
SEND_BUFF_SIZE = 8192
RECV_BUFF_SIZE = 8192
ALPHA = 1/8
BETA = 1/4
@dataclass
class RCV(object):
	MSS : int = 536 #maximum segment size set to be the default
	NXT : int = 0	#receive next
	WND : int = 0	#receive window
	IRS : int = 0	#initial receive sequence number

@dataclass
class SND(object):
	MSS : int = 536 #maximum segment size set to be the default
	UNA : int = 0	#send unacknowledged
	NXT : int = 0	#send next
	WND : int = 0	#send window
	WL1 : int = 0	#segment sequence number used for last window update
	WL2 : int = 0	#segment acknowledgment number used for last window update
	ISS : int = 0	#initial send sequence number
class Timer():
	def __init__(self, name):
		self.timer_length = 0
		self.start_time = None
		self.name = name
	def set_length(self, length):
		self.timer_length = length
	def stop_timer(self):
		self.start_time = None
	def time_up(self):
		if self.start_time == None:
			return False
		return time.time() - self.start_time > self.timer_length
	def reset_timer(self):
		self.start_time = time.time()
	def is_runnning(self):
		return self.start_time != None
	def check_time(self):
		return time.time() - self.start_time
	def set_and_start(self, length):
		self.set_length(length)
		self.reset_timer()
class TCP_Connection():
	def __init__(self, self_address, dst_address, self_seq_num, dst_seq_num, log_file=None):
		#we do not implement real connections for this project, this is a psuedo-handshake
		#make sure that src_seq_num and dst_seq_num are set correctly
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.sock.bind(self_address)
		# self.sock.connect(dest_address)
		self.dest = dst_address
		self.SRC = self_address[1]
		#normally we would get this from the handshake, instead we set it to a defined value
		self.DST = dst_address[1]
		#send and receive flow control
		self.SND = SND()
		self.RCV = RCV()
		#this is a constant
		#normally we would get this from the handshake, instead we set it to a defined value
		self.SND.ISS = self_seq_num
		#this is the first unackledged byte
		self.SND.UNA = self.SND.ISS	#send unacknowledged, the first byte of acknoldeged data
		self.SND.NXT = self.SND.ISS	#send next, the next byte we want to send
		#send window, the maximum number of bytes we can send due to flow control (the flow control window)
		#normally we would get this from the handshake, instead we set it to a defined value
		self.SND.WND = RECV_BUFF_SIZE	
		self.SND.WL1 = dst_seq_num	#segment sequence number used for last window update
		self.SND.WL2 = self_seq_num	#segment acknowledgment number used for last window update
		#initial sequence number, also a constant
		#normally we would get this from the handshake, instead we set it to a defined value
		self.RCV.IRS = dst_seq_num
		#this is the next byte we expect, ie the sequence number of the first None in our recieve buffer
		self.RCV.NXT = self.RCV.IRS
		#this is the number of bytes after the first None in our receive buffer
		#[1, None, None, 2,3] RCV.WND =4
		self.RCV.WND = RECV_BUFF_SIZE
		#send and receive buffers
		self.receive_buffer = deque([None for x in range(self.RCV.WND)]) 
		self.send_buff = [] 
		#where to start reading from the receive buffer, ie the first sequence number in our receive buffer
		self. receive_buffer_start_seq= self.RCV.NXT
		#Timers
		#this times the last time we sent data, if it has been too long, we send an emtpy segment
		self.window_timer = Timer('Window')
		self.window_timer.set_length(1)
		#contains the data from the last sent packet
		#if we want to resend a data due to the window timer going off, we need to save it since it might already be gone
		#from the send buffer
		#the 3 variables here represent the 3 arguments to _packetize_and_send()
		self.last_packet = [-1, False, b'']
		#RTO calculation
		#this is the RTO timer
		self.RTO_timer = Timer('RTO')
		self.window_timer.set_length(1)
		#this times 1 segment at a time to time RTT
		#if you send new data and the timer is not running, start it
		#if the data you sent gets acknowledged, see how much time is left, that is the most recent RTT measurement
		#stop the timer
		self.RTT_timer = Timer('RTT')
		#the packet number that we are currently timing
		self.RTT_Sequence_num = -1
		self.SRTT = None
		self.RTTVAR = None
		# Conjestion Control
		self.congestion_window = 4 * self.SND.MSS
		self.SSTHRESH = None
		#wheather the socket is closed
		self.closed = False
		#The log file and the log timer
		self.log_file = log_file
		if log_file:
			self.log_timer = Timer('Log')
			self.log_timer.reset_timer()
		#one free use parameter
		self.temp = 0
	def _main_loop(self):
		#in this function we get all received data and proccess it.
		#we also check all timers and send all outstanding packets 
		#Step 0:if the other side is gone, nothing to do
		if self.closed:
			return
		#Step 1:check for received packets
		read_sockets, _, _ = select.select([self.sock], [], [], 0)
		incoming = []
		while read_sockets:
			if self.closed:
				break
			try:
				seg = self.sock.recv(self.RCV.MSS + 40)
			except:
				print('other socket closed')
				self.close()
				break
			if not seg:
				self.close()
			else:
				incoming.append(TCP_Segment(seg))
				if self.log_file:
					with open(self.log_file, 'a') as out_put:
						out_put.write(f'receiving at time {self.log_timer.check_time()}\n')
						out_put.write(str(incoming[-1]) + '\n') 
			read_sockets, _, _ = select.select([self.sock], [], [], 0)
		self.receive_packets(incoming)
		#Step 2 check on the timers:
		#The RTO timer handles the case where we don't have any response and it has been too long
		if self.RTO_timer.time_up():
			self.handle_timeout()
		#the window timer handles the case where it has been too long and we haven't sent any data
		if self.window_timer.time_up():
			#print(self.window_timer.check_time())
			self.handle_window_timeout()
		#Step 3 send packets
		#if it makes sense, send some data
		if self.send_buff:
			self.send_data()
	def _packetize_and_send(self, seq, PSH=False, data=b''):
		#this is the only way you should ever send packets, do not modify this function or use any other method to send
		to_send = TCP_Segment()
		to_send.SRC = self.SRC
		to_send.DST = self.DST
		to_send.SEQ = seq
		to_send.ACK = self.RCV.NXT
		to_send.flags.ACK = True
		to_send.flags.PSH = PSH
		to_send.WND = self.RCV.WND
		to_send.data = data
		if self.log_file:
			with open(self.log_file, 'a') as out_put:
				out_put.write(f'sending a time {self.log_timer.check_time()}\n')
				out_put.write(str(TCP_Segment(to_send.to_bytes())) + '\n')
		if not self.closed: 
			self.sock.sendto(to_send.to_bytes(), self.dest)
	def close(self):
		self.sock.close()
		self.closed = True
	def send(self, data, PUSH=False):
		#this code loads data into the send buffer.
		if self.closed:
			return
		if len(self.send_buff) + len(data) > SEND_BUFF_SIZE:
			return False
		for datum in data: 
			self.send_buff.append(datum)
		if PUSH:
			self.send_buff[-1] = bytes([self.send_buff[-1]] + list(b'PSH'))

		#data passed was b'\x01\x02\x03' push = True
		#send buffer will read [1,2,b'3PSH']
		#if we wanted to send it in one packet, we can call
		#self._packetize_and_send(x, PSH=True, data=b'\x01\x02\x03')
		#len(send_buffer) == #of bytes left to send
		#easy to check if a byte is pushed
		#drain the send buffer
		while self.send_buff:
			# print("send loop")
			self._main_loop()
		return True
	def recv(self, buff_size):
		#in this function we load data from the receive buffer into a new array, 
		#when the array is full or we see a push we give the data to the client
		#if the receive buffer empties too soon, we try to get more data
		if self.RCV.NXT == self.receive_buffer_start_seq and self.closed:
			return b''
		to_ret = bytearray()
		need_data = buff_size > 0 
		no_push = True
		while need_data and no_push:
			self._main_loop()
			have_data = self.receive_buffer_start_seq < self.RCV.NXT
			need_data = len(to_ret) < buff_size
			while have_data and need_data and no_push:
				data = self.receive_buffer.popleft()
				self.receive_buffer.append(None)
				#lets say receive buffer looks like [1,2,None,None,3]
				#if you get a new pacekt, just replace the nones with the contents
				if not isinstance(data, int) and data.endswith(b'PSH'):
					no_push = False 
					data = data[0]
				to_ret.append(data)
				#we now have more space in the receive buffer:
				self.RCV.WND += 1
				#we also have less data there
				self.receive_buffer_start_seq += 1
				have_data = self.receive_buffer_start_seq < self.RCV.NXT
				need_data = len(to_ret) < buff_size
			# if RECV_BUFF_SIZE - self.RCV.NXT + self.receive_buffer_start_seq - RCV.WND >= min( 0.5 * RECV_BUFF_SIZE, self.SND.MSS ):
			if self.closed:
				break
		return bytes(to_ret)

if __name__ == '__main__':
	if os.path.exists('send_packets.log'):
		os.remove('send_packets.log')
	tcp_sender = TCP_Connection((socket.gethostname(), 5001), (socket.gethostname(), 5055), 578430997, 2356389583, log_file='send_packets.log')
	line = b'blah'
	tcp_sender.send(bytes([i % 256 for i in range(600)]) , True)
	# while line:
	# 	line = tcp_sender.recv(512)
	# 	print(line)