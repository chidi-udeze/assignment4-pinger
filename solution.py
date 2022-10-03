from socket import *
import os
import sys
import struct
import time
import select
import binascii
import pandas as pd

ICMP_ECHO_REQUEST = 8

def checksum(string):
    csum = 0
    countTo = (len(string) // 2) * 2
    count = 0

    while count < countTo:
        thisVal = (string[count + 1]) * 256 + (string[count])
        csum += thisVal
        csum &= 0xffffffff
        count += 2

    if countTo < len(string):
        csum += (string[len(string) - 1])
        csum &= 0xffffffff

    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer

def receiveOnePing(mySocket, ID, timeout, destAddr):
    timeLeft = timeout

    while 1:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        if whatReady[0] == []:  # Timeout
            return "Request timed out."

        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)

        # Fill in start
        # Fetch the ICMP header from the IP packet
        icmpHeader = recPacket[20:28]
        rawTTL = struct.unpack("s", recPacket[20:21])[0]
        # binascii -- Convert between binary and ASCII
        TTL = int(binascii.hexlify(rawTTL), 16)
        icmpType, code, checksum, packetID, sequence = struct.unpack(
            "bbHHh", icmpHeader
        )

        if packetID == ID:
            bytes = struct.calcsize("d")
            timeSent = struct.unpack("d", recPacket[28 : 28 + bytes])[0]
            delay = "Reply from %s: bytes=%d time=%f5ms TTL=%d" % (
                destAddr,
                len(recPacket),
                (timeReceived - timeSent) * 1000,
                TTL,
            )
            return delay, len(recPacket), (timeReceived - timeSent) * 1000, TTL

        # Fill in end
        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return "Request timed out."


def sendOnePing(mySocket, destAddr, ID):
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)

    myChecksum = 0
    # Make a dummy header with a 0 checksum
    # struct -- Interpret strings as packed binary data
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    data = struct.pack("d", time.time())
    # Calculate the checksum on the data and the dummy header.
    myChecksum = checksum(header + data)

    # Get the right checksum, and put in the header

    if sys.platform == 'darwin':
        # Convert 16-bit integers from host to network  byte order
        myChecksum = htons(myChecksum) & 0xffff
    else:
        myChecksum = htons(myChecksum)


    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data

    mySocket.sendto(packet, (destAddr, 1))  # AF_INET address must be tuple, not str

    # Both LISTS and TUPLES consist of a number of objects
    # which can be referenced by their position number within the object.

def doOnePing(destAddr, timeout):
    icmp = getprotobyname("icmp")

    # SOCK_RAW is a powerful socket type. For more details:   https://sock-raw.org/papers/sock_raw
    mySocket = socket(AF_INET, SOCK_RAW, icmp)

    myID = os.getpid() & 0xFFFF  # Return the current process i
    sendOnePing(mySocket, destAddr, myID)
    delay, bytes, rtt, ttl = receiveOnePing(mySocket, myID, timeout, destAddr)
    mySocket.close()
    stats = {"bytes": bytes, "rtt": rtt, "ttl": ttl}
    return delay, stats

def ping(host, timeout=1):
    # timeout=1 means: If one second goes by without a reply from the server,   
    # the client assumes that either the client's ping or the server's pong is lost
    dest = gethostbyname(host)
    print("\nPinging " + dest + " using Python:")
    print("")
    
    # This creates an empty dataframe with 3 headers with the column specific names declared
    response = pd.DataFrame(
        columns=["bytes", "rtt", "ttl"]
    )
    #Send ping requests to a server separated by approximately one second
    #Add something here to collect the delays of each ping in a list so you can calculate vars after your ping
    
    for i in range(0,4): #Four pings will be sent (loop runs for i=0, 1, 2, 3)
        delay, statistics = doOnePing(dest, timeout) 
        #what is stored into delay and statistics?
        #store your bytes, rtt, and ttle here in your response pandas dataframe. An example is commented out below for vars
        response = response.append(statistics, ignore_index=True)
        print(delay) 
        time.sleep(1)
    
    packet_lost = 0
    packet_recv = 0
    #fill in start. UPDATE THE QUESTION MARKS
    for index, row in response.iterrows():
        if row.get("rtt") and row["rtt"] == 0: #access your response df to determine if you received a packet or not
            packet_lost = packet_lost + 1
        else:
            packet_recv = packet_recv + 1
    #fill in end

    #You should have the values of delay for each ping here structured in a pandas dataframe; 
    #fill in calculation for packet_min, packet_avg, packet_max, and stdev
    vars = pd.DataFrame(columns=['min', 'avg', 'max', 'stddev'])
    vars = vars.append({'min':str(round(response['rtt'].min(), 2)), 'avg':str(round(response['rtt'].mean(), 2)),'max':str(round(response['rtt'].max(), 2)), 'stddev':str(round(response['rtt'].std(),2))}, ignore_index=True)
    print (vars) #make sure your vars data you are returning resembles acceptance criteria
    return vars

if __name__ == '__main__':
    ping("google.com")