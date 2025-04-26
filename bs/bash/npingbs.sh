#!/bin/bash

# Essentially one-directional ping. Use for cal.
# Self-Cal:
# sudo bash npingbs.sh wlp6s0 10:5f:ad:d6:a3:2b 10.255.255.255
# Ping Laptop:
# sudo bash npingbs.sh wlp4s0 8c:e9:ee:d9:a2:e2 10.42.0.56

SRC_IFACE=$1
SRC_MAC="6c:2f:80:df:37:ca" # Reference MAC Address
DST_MAC=$2 #"10:5f:ad:d6:a3:2b" (Hotspot MAC Address)
DST_IP=$3 #"10.255.255.255" 
PING_RATE=7000 #PING_RATE packets per second
NUM_PACKETS=$(($PING_RATE*60)) # 1 Minute's worth of packets.

echo "Testing with nping on: $1"

# Burst for 4 (To Start), 0.1s interval.
echo "Burst 4 frames with 0.1s interval."
sudo nping --source-mac $SRC_MAC --dest-mac $DST_MAC --ether-type 0x0800 --interface $SRC_IFACE --send-eth --data-length 0 --rate 10 -c 4 $DST_IP

echo ""
sleep 0.5

# Continuous Ping.
echo "Sending ${NUM_PACKETS} Packets at ${PING_RATE} Packets per second."
sudo nping --source-mac $SRC_MAC --dest-mac $DST_MAC --ether-type 0x0800 --interface $SRC_IFACE --send-eth --data-length 100 --rate $PING_RATE -c $NUM_PACKETS $DST_IP

echo ""
sleep 0.5

# Burst for 4 (To Finish)
echo "Burst 4 frames with 0.1s interval."
sudo nping --source-mac $SRC_MAC --dest-mac $DST_MAC --ether-type 0x0800 --interface $SRC_IFACE --send-eth --data-length 100 --rate 10 -c 4 $DST_IP

echo ""
echo "DONE!"
