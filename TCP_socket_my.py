from TCP_socket_p2 import TCP_Connection
from TCP_socket_p2 import TCP_Segment
from typing import List
from threading import current_thread

class TCP_Connection_Final(TCP_Connection):
	"""docstring for TCP_Connection_Final"""
	def __init__(self, self_address, dst_address, self_seq_num, dst_seq_num, log_file=None):
		super().__init__(self_address, dst_address, self_seq_num, dst_seq_num, log_file)
	def handle_timeout(self):
		#put code to handle RTO timeout here

		# send a single packet containing the oldest unacknowledged data
		allow_send_len = min(self.SND.MSS, self.SND.WND, self.congestion_window, len(self.send_buff))
		if allow_send_len <= 0:
			return

		print(current_thread().ident, "handle_timeout allow_send_len:", allow_send_len)

		# set PSH
		PSH_FLAG = False
		# data = self.send_buff[:allow_send_len]
		data = []
		for i in range(allow_send_len):
			if isinstance(self.send_buff[i], bytes):
				PSH_FLAG = True
				data.append(self.send_buff[i][0])
			else:
				data.append(self.send_buff[i])
		
		print(self.SND.UNA, PSH_FLAG)
		print("data:", data)
		
		self._packetize_and_send(self.SND.UNA, PSH_FLAG, bytes(data))
		
		# save last packet for window timeout
		self.last_packet[:]= [self.SND.UNA, PSH_FLAG, bytes(data)]


		# increase the RTO timer 
		self.RTO_timer.set_and_start(self.RTO_timer.timer_length * 2)

		pass
	def handle_window_timeout(self):
		#put code to handle window timeout here
		#in other words, if we haven't sent any data in while (which causes this time to go off),
		#send an empty packet

		print(current_thread().ident, "handle_window_timeout allow_send_len:", self.last_packet[0])

		self._packetize_and_send(self.last_packet[0], self.last_packet[1], self.last_packet[2])

		self.window_timer.set_and_start(self.window_timer.timer_length * 2)
		pass
	def receive_packets(self, packets: List[TCP_Segment]):
		#insert code to deal with a list of incoming packets here
		#NOTE: this code can send one packet, but should never send more than one packet

		# print("receive_packets:", len(packets))
		if len(packets) == 0:
			return

		# 100 101 None Non None None None
		# [105 106 107 108]
		recv_new_bytes = False
		for i in range(len(packets)):

			# RFC9293 p56
			# The check here prevents using old segments to update the window.
			# self.SND.WND = packets[i].WND
			
			if packets[i].ACK >= self.SND.UNA and packets[i].ACK <= self.SND.NXT:
				if self.SND.WL1 < packets[i].SEQ or (self.SND.WL1 == packets[i].SEQ and self.SND.WL2 <= packets[i].ACK):
					self.SND.WND = packets[i].WND
					self.SND.WL1 = packets[i].SEQ
					self.SND.WL2 = packets[i].ACK
				else:
					print("bad packet 1: ", packets[i].SEQ, self.SND.WL1, self.SND.WL2)
					continue
			else:
				print("bad packet 2: ", packets[i].ACK, self.SND.UNA, self.SND.NXT)
				continue

			if len(packets[i].data) > 0:
				recv_new_bytes = True

			# save left bytes according to the current recv window
			# spare_bytes = self.RCV.WND - (packets[i].SEQ - self.receive_buffer_start_seq)
			spare_bytes = len(self.receive_buffer) - (packets[i].SEQ - self.receive_buffer_start_seq)
			if spare_bytes == 0:
				print(current_thread().ident, "spare_bytes 0: ", packets[i].SEQ, self.receive_buffer_start_seq)
				recv_new_bytes = True
				break
			print(current_thread().ident, "recv info: ", len(self.receive_buffer), spare_bytes, self.RCV.WND, self.receive_buffer_start_seq)
			if spare_bytes < len(packets[i].data):
				packets[i].data = packets[i].data[0:spare_bytes]
			
			# copy bytes to recv buffer
			for j in range(len(packets[i].data)):
				self.receive_buffer[packets[i].SEQ - self.receive_buffer_start_seq + j] = packets[i].data[j]
			# check PSH flag
			if packets[i].flags.PSH:
				self.receive_buffer[packets[i].SEQ - self.receive_buffer_start_seq + len(packets[i].data) - 1] = bytes([packets[i].data[-1]] + list(b'PSH'))

			# When an ACK is received that acknowledges new data, restart the retransmission timer [rfc6928 5.3]
			if packets[i].ACK:
				print(current_thread().ident, " recv ack: ", packets[i].SEQ + len(packets[i].data), self.RCV.NXT)
				if packets[i].SEQ + len(packets[i].data) >= self.RCV.NXT:
					self.RTO_timer.reset_timer()
					print(current_thread().ident, "recv new ack reset_timer ")

			# recv new bytes
			if packets[i].SEQ + len(packets[i].data) > self.RCV.NXT:
				recv_new_bytes = True


			# update SND.UNA by received ACK
			# [100, None, None, 103, None]
			# [101, 102]
			# [104]
			# newAck = False
			if packets[i].ACK > self.SND.UNA:
				# delete una buffer
				print(current_thread().ident, "recv ack update send_buff: ", packets[i].ACK, self.SND.UNA)
				self.send_buff = self.send_buff[packets[i].ACK - self.SND.UNA:]
				# update una
				self.SND.UNA = packets[i].ACK
				# newAck = True
			else:
				print(current_thread().ident, "recv repeated ack: ", packets[i].ACK, self.SND.UNA)
			
			# check zero probing window
			# if newAck:
			if packets[i].WND <= 0:
				if not self.window_timer.is_runnning():
					print(current_thread().ident, "start window timer")
					self.window_timer.set_and_start(1)
			else:
				if self.window_timer.is_runnning():
					print(current_thread().ident, "recv window > 0 stop window timer")
					self.window_timer.stop_timer()
			# update RTT


		# update RCV.NXT which is the seq of the first 'None' in the 'receive_buffer'
		# print("self.receive_buffer len: ", len(self.receive_buffer))
		seeNone = False
		for i in range(len(self.receive_buffer)):
			if self.receive_buffer[i] == None:
				self.RCV.NXT = i + self.receive_buffer_start_seq
				seeNone = True
				break
		if not seeNone:
			self.RCV.NXT = self.receive_buffer_start_seq + len(self.receive_buffer)
			print(current_thread().ident, "we have full receive_buffer:", self.RCV.NXT, self.receive_buffer_start_seq, len(self.receive_buffer))

		# update RCV.WND
		# TODO delete 8192 use name
		self.RCV.WND = len(self.receive_buffer) - (self.RCV.NXT - self.receive_buffer_start_seq)
		
		print(current_thread().ident, "self.receive NXT start_seq self.RCV.WND : ", self.RCV.NXT, self.receive_buffer_start_seq, self.RCV.WND)
		
		# send ACK
		if recv_new_bytes:
			self._packetize_and_send(seq=self.SND.UNA)

			# close RTO timer when we recv all acks for sent data [rfc6298 5.2]
			if self.SND.UNA >= self.SND.NXT:
				self.RTO_timer.stop_timer()


		pass
	def send_data(self, window_timeout = False, RTO_timeout = False):
		#put code to send a single packet of data here
		#note that this code does not always need to send data, only if TCP policy thinks it makes sense
		#if there is any data to send, i.e. we have data we have not sent and we are allowed to send by our
		#congestion and flow control windows, then send one packet of that data
		
		allow_send_len = min(self.SND.MSS, self.SND.WND, self.congestion_window, len(self.send_buff) - (self.SND.NXT - self.SND.UNA))
		if allow_send_len <= 0:
			return

		if self.SND.NXT >= self.SND.UNA + self.SND.WND:
			# exit()
			# print("no bytes with sequence numbers greater than SND.UNA + SND.WND should ever be sent: ", self.SND.NXT, self.SND.UNA, self.SND.WND)
			return

		print(current_thread().ident, "allow_send_len:", allow_send_len, self.SND.NXT, self.SND.UNA, self.SND.WND)

		# set PSH
		PSH_FLAG = False
		# data = self.send_buff[:allow_send_len]
		data = []
		for i in range(allow_send_len):
			if isinstance(self.send_buff[self.SND.NXT - self.SND.UNA + i], bytes):
				PSH_FLAG = True
				data.append(self.send_buff[self.SND.NXT - self.SND.UNA + i][0])
			else:
				data.append(self.send_buff[self.SND.NXT - self.SND.UNA + i])
		
		print(self.SND.NXT, PSH_FLAG)
		# print("data:", data)

		
		self._packetize_and_send(self.SND.NXT, PSH_FLAG, bytes(data))
		
		# save last packet for window timeout
		self.last_packet[:]= [self.SND.NXT, PSH_FLAG, bytes(data)]


		# check RTO timer
		if not self.RTO_timer.is_runnning():
			self.RTO_timer.set_and_start(1)

		# self._packetize_and_send(self.last_packet[0], self.last_packet[1], self.last_packet[2])

		self.SND.NXT = self.SND.NXT + allow_send_len

		pass
