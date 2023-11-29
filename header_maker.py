import argparse
from sys import argv
import socket
import struct
from dataclasses import dataclass
import pickle
from random import randint

def chksum(packet: bytes) -> int:
	if len(packet) % 2 != 0:
		packet += b'\0'
	total = 0
	for i in range(0, len(packet), 2):
		total += int.from_bytes(packet[i:i+2], 'big')
		if total >= 0x10000:
			total += 1
			total = total & 0xffff
	return(~total) & 0xffff

	return (~res) & 0xffff
def print_IP_Header(base_header):
	print('basic_info, length, identification, fragment, TTL, Protocol, CKSUM')
	print(struct.unpack('!HHHHBBH', base_header[:12]))
	print('SRC_IP, DEST_IP')
	print(socket.inet_ntoa(base_header[12:16]), socket.inet_ntoa(base_header[16:20]))
def make_IP_Header(packet_data, SRC, DEST, protocol):
	base_header = b'E\x00\x00 \x03\xeb\x00\x00\x80\x11\x00\x00\x7f\x00\x00\x01\x7f\x00\x00\x01'
	basic_info, length, identification, fragment, TTL, _, CKSUM, SRC_IP, DEST_IP =  struct.unpack('!HHHHBBHII', base_header)
	# print(struct.unpack('!HHHHHHII', base_header))
	new_id = randint(0, 65535)
	# tmp = struct.pack('!HHHHHH', basic_info, len(packet_data) + 20, new_id, fragment, TTL, 0) 
	return struct.pack('!HHHHBBH', basic_info, len(packet_data) + 20, new_id, fragment, TTL, protocol, 0) + socket.inet_aton(SRC) + socket.inet_aton(DEST)
def get_cheksum(packet, src, dest, protocol):

	pseudo_hdr = struct.pack(
		'!4s4sHH',
		src,	# Source Address
		dest,	# Destination Address
		protocol,				 # PTCL
		len(packet)						 # TCP Length
	)
	# print(len(packet))
	# print(pseudo_hdr + packet)
	# print(f'**{pseudo_hdr}**')
	# print(f'--{packet}--')
	return chksum(pseudo_hdr + packet)

@dataclass
class TCP_flags(object):
	"""docstring for TCP_flags"""
	FIN : bool
	SYN : bool
	RST : bool
	PSH : bool
	ACK : bool
	URG : bool
	ECE : bool
	CWR : bool
	def __repr__(self):
		variables = vars(self)
		return ','.join([var for var in variables if variables[var]])

class TCP_Segment(object):
	"""docstring for TCP_Segment"""
	def __init__(self, segment_as_bytes=None, protocol=6):
		# self.unpack_flags(segment_as_bytes)
		self.protocol = protocol
		if segment_as_bytes and protocol == 6:
			self.SRC, self.DST, self.SEQ, self.ACK, offset, flags, self.WND, self.CKSUM, self.UP = TCP_Segment.get_variables_from_bytes(segment_as_bytes[:20])
			self.offset = TCP_Segment.get_offset(offset)
			if self.offset > 5:
				self.options = TCP_Segment.get_options(segment_as_bytes[20:self.offset * 4])
			else:
				self.options = []
			self.data = segment_as_bytes[self.offset * 4:]
			self.flags = TCP_Segment.get_flags(flags) 
			self.LEN = len(self.data)
		elif segment_as_bytes and protocol == 17:
			self.SRC, self.DST, self.LEN, self.CKSUM = struct.unpack('!HHHH', segment_as_bytes[:8])
			self.data = segment_as_bytes[8:self.LEN + 8]
		elif (not segment_as_bytes) and protocol == 6:
			self.SRC, self.DST, self.SEQ, self.ACK, offset, flags, self.WND, self.CKSUM, self.UP = TCP_Segment.get_variables_from_bytes(bytearray(20))
			self.offset = TCP_Segment.get_offset(offset)
			if self.offset > 5:
				self.options = TCP_Segment.get_options(segment_as_bytes[20:self.offset * 4])
			else:
				self.options = []
			self.data = b''
			self.flags = TCP_Segment.get_flags(0) 
			self.LEN = 0
		elif (not segment_as_bytes) and protocol == 17:
			self.SRC, self.DST, self.LEN, self.CKSUM = struct.unpack('!HHHH', bytearray(8))
			self.data = b''


	@staticmethod
	def get_variables_from_bytes(header):
		return struct.unpack('!HHIIBBHHH', header)
	def recompute_values(self):
		self = TCP_Segment(self.to_bytes())
	@staticmethod
	def get_offset(offset):
		return offset >> 4
	#FOR NOW DOES NOT SUPPORT ADDING OR REMOVING OPTIONS SINCE THAT WILL NOT BE NEEDED FOR THE PROJECT
	def to_options_bytes(self):
		if not self.options:
			return b''
		option_bytes = bytearray()
		for option in self.options:
			option_bytes += option['kind'].to_bytes(1, byteorder='big')
			if 'length' in option:
				option_bytes += option['length'].to_bytes(1, byteorder='big')
				if 'value' in option:
					option_bytes += option['value'].to_bytes(2, byteorder='big')
				else:
					option_bytes += option['data']
		return bytes(option_bytes)
	@staticmethod
	def get_options(options):
		options_array = bytearray(options)
		options = []
		while options_array:
			next_byte = options_array[0]
			option = {'kind':next_byte}
			options_array.pop(0)
			if option['kind'] == 1:
				option['name'] = 'No-Operation'
			elif option['kind'] == 1:
				option['name'] = 'End-of-Options'
			else:
				option['length'] = options_array[0]
				option['data'] = options_array[1:option['length'] - 1]
				options_array = options_array[option['length'] - 1:]
				if option['kind'] == 2:
					option['name'] = 'Maximum Segment Size'
					option['value'] = int.from_bytes(option['data'], 'big')
			options.append(option)
		return options
	def pack_flags(self):
		answer = 0x0000
		answer |= self.flags.FIN & 0x1
		answer |= (self.flags.SYN & 0x1) << 1
		answer |= (self.flags.RST & 0x1) << 2
		answer |= (self.flags.PSH & 0x1) << 3
		answer |= (self.flags.ACK & 0x1) << 4
		answer |= (self.flags.URG & 0x1) << 5
		answer |= (self.flags.ECE & 0x1) << 6
		answer |= (self.flags.CWR & 0x1) << 7
		return answer
	def to_UDP_bytes(self):
		print('UDP bytes')
		header = struct.pack('!HHHH', self.SRC, self.DST, len(self.data) + 8, self.CKSUM)
		return header + self.data
	@staticmethod
	def get_flags(flag_byte):
		answer_dict = {}
		answer_dict['FIN'] = flag_byte & 0x1
		flag_byte >>= 1
		answer_dict['SYN'] = flag_byte & 0x1
		flag_byte >>= 1
		answer_dict['RST'] = flag_byte & 0x1
		flag_byte >>= 1
		answer_dict['PSH'] = flag_byte & 0x1
		flag_byte >>= 1
		answer_dict['ACK'] = flag_byte & 0x1
		flag_byte >>= 1
		answer_dict['URG'] = flag_byte & 0x1
		flag_byte >>= 1
		answer_dict['ECE'] = flag_byte & 0x1
		flag_byte >>= 1
		answer_dict['CWR'] = flag_byte & 0x1
		flags = TCP_flags(**answer_dict)
		return flags
	def to_bytes(self):
		if self.protocol == 17:
			return self.to_UDP_bytes()
		elif self.protocol == 6:
			options = self.to_options_bytes()
			offset = ((20 + len(options)) // 4) << 4 
			flags = self.pack_flags()
			#INTENTIONALLY DOES NOT COMPUTE CHECKSUM, see project 1
			header = struct.pack('!HHIIBBHHH', self.SRC, self.DST, self.SEQ, self.ACK, offset, flags, self.WND, self.CKSUM, self.UP) + options
			return  header + self.data
	def __repr__(self):
		return str(vars(self))


		

if __name__ == '__main__':
	with open('convo.p', 'rb') as log:
		raw_messages = pickle.load(log)
	messages = [TCP_Segment(message[20:]) for message in raw_messages]
	for message in messages:
		print(message)
	for i,mess in enumerate(messages):
		print('-----')
		if mess.to_bytes() == raw_messages[i][20:]:
			print('Success')
			print(mess)
			print(mess.to_bytes())
			print(raw_messages[i][20:])
		else:
			print(mess.to_bytes())
			print(raw_messages[i][20:])
			for j,item in enumerate(mess.to_bytes()):
				if item != raw_messages[i][j + 20]:
					print(j)
					print(item, raw_messages[i][j + 20])
					print(format(item, 'b'))
					exit(0)
	# print(messages)

         