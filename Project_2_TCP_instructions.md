The goal of this project is to implement a pared down version of TCP. This project will be worth 13 points. You will need information from the following 
RFCs:
https://www.rfc-editor.org/rfc/rfc5681
https://www.rfc-editor.org/rfc/rfc9293
https://www.rfc-editor.org/rfc/rfc6298
I have tried to limit the amount of work needed in several ways. 
0. I have attached a significant amount of code to help you. 
1. there are some features of TCP we will be leaving out. Most importantly, we will not be implementing connections. This means that the sequence numbers must be passed out of band. 
2. We also won't implement the SWS avoidance algorithms. 
3. We won't be implementing duplicate acks among other optional features. 

Here are the functions we WILL be implementing:
0. Send packets: Load the correct data from the send buffer and send the largest packet that 3 factors allow, min([maximum segment size(SND.MSS), flow_control_window (SND.WND), congestion_control_window (self.congestion_window)], how many data u have) Note: this may be no data at all, in which case no packet should be sent.

1. Receive packets: Read packet data into the receive buffer as described below. Remember to always put data in the spot indicated by its sequence number (after subtracting self.receive_buffer_start_seq). Also remember that not all packets will fall evenly along boundaries; they should therefore be trimmed so that any bytes that lie in the receive window are read into the receive buffer at the right place and the other bytes are discarded.

2. Congestion control: Update congestion control window as per RFC, never send more bytes than the congestion control window (https://www.rfc-editor.org/rfc/rfc5681)
    2a.RTT timer: Set the RTT timer (as described in class)
		if you send new data and the timer is not running, start it
		if the data you sent gets acknowledged, see how much time has passed. That amount of time becomes the new most recent RTT measurement, and should be used for future updates of the RTO timer(https://www.rfc-editor.org/rfc/rfc6298)
    2b.RTO timer: Set the RTO timer correctly and update as per RFC (https://www.rfc-editor.org/rfc/rfc6298)

3. Resend packets: Whenever the RTO timer goes off, resend 1 packet containing the oldest unacked data(https://www.rfc-editor.org/rfc/rfc6298)

4. Flow control: Never send more data then the flow control window; no bytes with sequence numbers greater than SND.UNA + SND.WND should ever be sent.
Update SND.WND when a new window measurement comes in, as per the RFC quote below
Update SND.UNA as described in the quoted RFC below, when new data is acknowledged

1 2 3 4 5

5. Push flag: 
	5a.Send: Set the push flag whenever at least one of the bytes you are sending is marked PSH. Remember to remove the marking in the actual sent data (https://www.rfc-editor.org/rfc/rfc9293#section-3.9.1.2).
	5b.Receive: Mark a byte with PSH as described in class when the packet has the PSH flag set. For example, if the data is b'\x01\x02\x03' and the PSH flag is set, the following bytes would go into the receive buffer [1, 2,b'\x03PSH'] (https://www.rfc-editor.org/rfc/rfc9293#name-receive)

6. Send correct acks, as described below, meaning whenever the list of packets contains new data send an acknowledgement (empty packet) with ack# = the next expected byte (RCV.NXT). Remember to only send one ack per a list of packets. When appropriate, update the next expected byte by incrementing RCV.NXT.

7. Zero window probing: If a window timer ever goes off, send a packet containing the most recent data you sent. When it goes off, increase the timer by a factor of 2 (just like the RTO timer). Whenever data is sent, including retransmissions, restart the timer setting it to the same time you would reset the RTO timer to if you got a new ack. (https://www.rfc-editor.org/rfc/rfc9293#section-3.8.6.1)

To divide it into what goes in each function:
	def handle_timeout(self):
		2b, 3, (7)
	def handle_window_timeout(self):
		7
	def receive_packets(self, packets):
		1,2a,2b,4,5b,6
	def send_data(self, window_timeout = False, RTO_timeout = False):
		0,2,2a,2b,4,5a,7

 I have approximately 2-10 lines for the timeout functions, ~20-30 lines for the send function, ~60 lines for receive packets. The logic for all functions except receive_packets should be relatively simple.


Please feel free to ask any questions you might have. Start early to make this possible to complete on time. You may only edit the TCP_socket_to_fill file, filling in the 4 required functions. You must leave the functions in the TCP_socket.py the same. You may add any additional functions that you find useful. However, you must not access the socket directly, only send data using _packetize_and_send the received packets will be passed into the receive function.

Testing will start with the included simple test. More tests will be released as the project progresses. I suggest you try to get the simple test working this weekend if you can. Don't worry if the times in the test don't line up exactly as long as they are within about 0.5 seconds of the given time.


Academic Dishonesty:

Code copied from anywhere will be dealt with according to the Rutgers Academic Dishonesty policy.
If the copied code's source is referenced, the maximum penalty will be 50% off the given assingment, 
and as little as nothing depending on how much was copied and whether you had the license.

If the code is not cited, and makes up a substantial portion of the project, the MINIMUM penalty will be
a zero on the assignment.


README file
-----------


In addition to your programs, you must also submit a README file (named README.txt) with clearly
delineated sections for the following.


0. Please write down the full names and netids of both your team members.
1. Are there known issues or functions that aren't working currently in your
   attached code? If so, explain. (note that you will get half credit for any reasonably sized bug that is fully explained in the readme)
2. Collaboration: Who did you collaborate with on this project? What resources and refer-
ences did you consult? Please also specify on what aspect of the project you collaborated or
consulted.
3. What problems did you face developing code for this project? Around how long did you spend on this project? (This helps me decide what I need to explain more clearly for the next projects)


Submission
----------


Turn in your project on Canvas assignments. Only one team member should submit. 
Please submit your final project as a single zip file with the exact following files inside it
 (the readme should be a text file)(Note caps in file and folder names).

Project_2
   -- TCP_socket_to_fill.py
   -- README.txt


Resources
----------
Here is a useful quote from the RFC about how to handle new incoming packets. Note that whenever the RFC says "return" you will want to use the continue keyword since you still must process all the other packets you received: 


First, check sequence number:
ESTABLISHED STATE 
Segments are processed in sequence. Initial tests on arrival are used to discard old duplicates, but further processing is done in SEG.SEQ order. If a segment's contents straddle the boundary between old and new, only the new parts are processed.
In general, the processing of received segments MUST be implemented to aggregate ACK segments whenever possible (MUST-58). For example, if the TCP endpoint is processing a series of queued segments, it MUST process them all before sending any ACK segments (MUST-59).

There are four cases for the acceptability test for an incoming segment:
            +=========+=========+======================================+
            | Segment | Receive | Test                                 |
            | Length  | Window  |                                      |
            +=========+=========+======================================+
            | 0       | 0       | SEG.SEQ = RCV.NXT                    |
            +---------+---------+--------------------------------------+
            | 0       | >0      | RCV.NXT =< SEG.SEQ <                 |
            |         |         | RCV.NXT+RCV.WND                      |
            +---------+---------+--------------------------------------+
            | >0      | 0       | not acceptable                       |
            +---------+---------+--------------------------------------+
            | >0      | >0      | RCV.NXT =< SEG.SEQ <                 |
            |         |         | RCV.NXT+RCV.WND                      |
            |         |         |                                      |
            |         |         | or                                   |
            |         |         |                                      |
            |         |         | RCV.NXT =< SEG.SEQ+SEG.LEN-1         |
            |         |         | < RCV.NXT+RCV.WND                    |
            +---------+---------+--------------------------------------+
In implementing sequence number validation as described here, please note Appendix A.2. If the RCV.WND is zero, no segments will be acceptable, but special allowance should be made to accept valid ACKs, URGs, and RSTs.

If an incoming segment is not acceptable, an acknowledgment should be sent in reply (unless the RST bit is set, if so drop the segment and return):
<SEQ=SND.NXT><ACK=RCV.NXT><CTL=ACK> After sending the acknowledgment, drop the unacceptable segment and return. Note that for the TIME-WAIT state, there is an improved algorithm described in [40] for handling incoming SYN segments that utilizes timestamps rather than relying on the sequence number check described here. When the improved algorithm is implemented, the logic above is not applicable for incoming SYN segments with Timestamp Options, received on a connection in the TIME-WAIT state. In the following it is assumed that the segment is the idealized segment that begins at RCV.NXT and does not exceed the window. One could tailor actual segments to fit this assumption by trimming off any portions that lie outside the window (including SYN and FIN) and only processing further if the segment then begins at RCV.NXT. Segments with higher beginning sequence numbers SHOULD be held for later processing (SHLD-31). (We are implementing SHLD-31)


Fifth, check the ACK field:
if the ACK bit is off, drop the segment and return

if the ACK bit is on,


ESTABLISHED STATE
If SND.UNA < SEG.ACK =< SND.NXT, then set SND.UNA <- SEG.ACK. Any segments on the retransmission queue that are thereby entirely acknowledged are removed. Users should receive positive acknowledgments for buffers that have been SENT and fully acknowledged (i.e., SEND buffer should be returned with "ok" response). If the ACK is a duplicate (SEG.ACK =< SND.UNA), it can be ignored. If the ACK acks something not yet sent (SEG.ACK > SND.NXT), then send an ACK, drop the segment, and return.
If SND.UNA =< SEG.ACK =< SND.NXT, the send window should be updated. If (SND.WL1 < SEG.SEQ or (SND.WL1 = SEG.SEQ and SND.WL2 =< SEG.ACK)), set SND.WND <- SEG.WND, set SND.WL1 <- SEG.SEQ, and set SND.WL2 <- SEG.ACK. Note that SND.WND is an offset from SND.UNA, that SND.WL1 records the sequence number of the last segment used to update SND.WND, and that SND.WL2 records the acknowledgment number of the last segment used to update SND.WND. The check here prevents using old segments to update the window.



Seventh, process the segment text:
ESTABLISHED STATE
Once in the ESTABLISHED state, it is possible to deliver segment data to user RECEIVE buffers. Data from segments can be moved into buffers until either the buffer is full or the segment is empty. If the segment empties and carries a PUSH flag, then the user is informed, when the buffer is returned, that a PUSH has been received.
When the TCP endpoint takes responsibility for delivering the data to the user, it must also acknowledge the receipt of the data. Once the TCP endpoint takes responsibility for the data, it advances RCV.NXT over the data accepted, and adjusts RCV.WND as appropriate to the current buffer availability. The total of RCV.NXT and RCV.WND should not be reduced. A TCP implementation MAY send an ACK segment acknowledging RCV.NXT when a valid segment arrives that is in the window but not at the left window edge (MAY-13). Please note the window management suggestions in Section 3.8.

Send an acknowledgment of the form:
<SEQ=SND.NXT><ACK=RCV.NXT><CTL=ACK> 


Here is an example of how sequence numbers work from class:
Host A
 12345678901234567
"Here is some data"

"H|ere| is so|me d|ata"

Host B
 2     1   5       15     11 
"ere" "H" " is so" "ata" "me d"