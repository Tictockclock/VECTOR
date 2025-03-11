#!/bin/bash

echo "Testing with iperf3 on: $1"


function ping {
# First burst: Send 4 small packets with 0.1s interval
for i in {1..4}; do
    iperf3 -c $1 -u -b 1M -l 100 -n 1000 >/dev/null 2>&1
    echo "burst $i"
    sleep 0.1
done

sleep 2

# Middle test: Send 1200 packets with 0.1s interval
for i in {1..1200}; do
    iperf3 -c $1 -u -b 1M -l 100 -n 1000 >/dev/null 2>&1
    echo "long $i"
    sleep 0.1
done

sleep 2

# Last burst: Send 4 small packets with 0.1s interval
for i in {1..4}; do
    iperf3 -c $1 -u -b 1M -l 100 -n 1000 >/dev/null 2>&1
    echo "burst $i"
    sleep 0.1
done
}

ping $1


echo "DONE!"
