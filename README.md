# a pared down version of TCP

## Qiyun Chen

### 07/20/2023

    @author Qiyun Chen | @netid qc104 | @version python3.9

1. No, my code works perfectly for all 3 test. This means Bytes match will be printed as stdout and send and recv logs for all 3 tests are as same as given logs.(except time, up or down 0.5sec)

    WATCH ME: RTO_test would generate one line different logs due to different network performance. If you find the generated logs for RTO_test are not same as given one. Try to run RTO_test again!!! This happened when I tested RTO_test. But it generated correct logs when I ran RTO_test again.

2. No collaborate for this one. Worked alone.  
    Reference:  
    RFCs:  
    https://www.rfc-editor.org/rfc/rfc5681  
    https://www.rfc-editor.org/rfc/rfc9293  
    https://www.rfc-editor.org/rfc/rfc6298

3. It takes me at least 50+ hours to pass all the tests. The difficulties are how to correct set each flag in SND and RCV. Also, how to send a correct ack and use correct WL1 and WL2 to find and handle bad packet(incorrect ack). And also threads taken by recv and send are different, I separately find them and display them when I debugged my program. For the Simple Test, how to set each flag is the hardest step, I have to determine correct seq and send size to send correct data. And using the "packets" to set data correctly in the recv_buffer, after receiving correct ack I also need to update send_buffer to make sure the acked data is removed from send_buffer. In RTO test, how to set and start timer and when should I start it are the hardest two implementation. I read RFC lots of time and debugged them a lot to set RTO timer correctly. In flow control test, since flow control is already implemented in Simple test(I did it correctly). The hardest part is how correctly set window timer and solve zero window probing. There are two diff ways, the first one is set and start window timer whenever a packet sent. The second one is when a ack packet with 0 WND size received, set and start a timer, when it times up, send last_packet(updated when any send happened) to get current WND size. When a positive WND size received, keep doing the regular process. I implemented both version. At first, I followed second approach, 0 WND size received then set and start timer. But, when I "diff" with test_3_send_expect.log, the time for sending 0 window probing packet is not correct. I recognized that the log means another approach. After discussion with Instructor Gale, I choose to keep the second one, which would generate perfect logs for test_3. And for the bad_packet, which has wrong seq, ack and window size. This packet influents our window timer with a wrong window size, if we didn't catch it. Thus, I successfully catch this bad_packet by only accepting the correct ack packets.