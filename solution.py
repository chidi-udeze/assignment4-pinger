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
        thisValue = (string[count + 1]) * 256 + (string[count])
        csum += thisValue
        csum &= 0xFFFFFFFF
        count += 2
    if countTo < len(string):
        csum += string[len(string) - 1]
        csum &= 0xFFFFFFFF
    csum = (csum >> 16) + (csum & 0xFFFF)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xFFFF
    answer = answer >> 8 | (answer << 8 & 0xFF00)
    return answer


def receiveOnePing(mySocket, ID, timeout, destAddr):
    timeLeft = timeout
    while 1:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = time.time() - startedSelect
        if whatReady[0] == []:  # Timeout
            return "Request timed out."
        timeReceived = time.time()
        recPacket, _ = mySocket.recvfrom(1024)  # recPacket, addr
        icmpHeader = recPacket[20:28]
        rawTTL = struct.unpack("s", recPacket[20:21])[0]
        TTL = int(binascii.hexlify(rawTTL), 16)
        # icmpType, code, checksum, packetID, sequence
        _, _, _, packetID, _ = struct.unpack("bbHHh", icmpHeader)
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
        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return "Request timed out."


def sendOnePing(mySocket, destAddr, ID):
    myChecksum = 0
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    data = struct.pack("d", time.time())
    myChecksum = checksum(header + data)
    if sys.platform == "darwin":
        myChecksum = htons(myChecksum) & 0xFFFF
    else:
        myChecksum = htons(myChecksum)
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data
    mySocket.sendto(packet, (destAddr, 1))


def doOnePing(destAddr, timeout):
    icmp = getprotobyname("icmp")
    mySocket = socket(AF_INET, SOCK_RAW, icmp)
    myID = os.getpid() & 0xFFFF
    sendOnePing(mySocket, destAddr, myID)
    delay, bytes, rtt, ttl = receiveOnePing(mySocket, myID, timeout, destAddr)
    mySocket.close()
    stats = {"bytes": bytes, "rtt": rtt, "ttl": ttl}
    return delay, stats


def ping(host, timeout=1):
    dest = gethostbyname(host)
    print("\nPinging " + dest + " using Python:")
    print("")
    response = pd.DataFrame(columns=["bytes", "rtt", "ttl"])
    for i in range(0, 4):
        delay, statistics = doOnePing(dest, timeout)
        response = response.append(statistics, ignore_index=True)
        print(delay)
        time.sleep(1)
    packet_lost = 0
    packet_recv = 0
    for index, row in response.iterrows():
        if row.get("rtt") and row["rtt"] == 0:
            packet_lost = packet_lost + 1
        else:
            packet_recv = packet_recv + 1
    vars = pd.DataFrame(columns=["min", "avg", "max", "stddev"])
    vars = vars.append(
        {
            "min": str(round(response["rtt"].min(), 2)),
            "avg": str(round(response["rtt"].mean(), 2)),
            "max": str(round(response["rtt"].max(), 2)),
            "stddev": str(round(response["rtt"].std(), 2)),
        },
        ignore_index=True,
    )
    print(vars)
    return vars


if __name__ == "__main__":
    ping("google.com")
