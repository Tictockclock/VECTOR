#!/bin/bash

# Run with sudo!
# sudo bash setupbs.sh wlp4s0 wlp5s0 wlp6s0 8

# Prepares Base Station for Calibration + Final Operation
# arg 1 ~ interface name for NIC associated with Hotspot
# arg 2 ~ interface name for NIC associated with Monitor (for Picoscenes)
# arg 3 ~ interface name for NIC associated with Reference (for Calibration)
# arg 4 ~ channel on which we operate

# Variables
HOTSPOT_NAME="dt12bs"
#^^^ -hotspot implied (added later)
HOTSPOT_PASSWORD="12345678"
AP_IFACE=$1
MON_IFACE=$2
REF_IFACE=$3
CHAN_NUM=$4

echo "Setting up $AP_IFACE as AP, $MON_IFACE for Monitor Mode, $REF_IFACE as the reference NIC."
echo "Setting up for channel: $CHAN_NUM"
echo ""

# Prevent the interfaces from turning off:
iw dev $AP_IFACE set power_save off
iw dev $MON_IFACE set power_save off
iw dev $REF_IFACE set power_save off

# Set the reference + hotspot to the chosen channel:
iwconfig $REF_IFACE channel $CHAN_NUM
nmcli connection modify ${HOTSPOT_NAME}-hotspot ifname $AP_IFACE
nmcli connection modify ${HOTSPOT_NAME}-hotspot 802-11-wireless.channel $CHAN_NUM

# Start the hotspot:
nmcli connection up dt12bs-hotspot

# Connect reference card to the hotspot
nmcli device wifi rescan ifname $REF_IFACE
sleep 0.5
nmcli device wifi rescan ifname $REF_IFACE
nmcli device wifi connect dt12bs ifname $REF_IFACE password $HOTSPOT_PASSWORD

# Set up the card in monitor mode:
# Find channel center frequency:
CENTER_FREQ=$(iw dev $AP_IFACE info | awk '/channel/ {print $9}')
CHAN_BW=$(iw dev $AP_IFACE info | awk '/channel/ {print $6}')
ARR_PREP_PICO_STR="${CENTER_FREQ} HT${CHAN_BW}"

echo "CENTER_FREQ: ${CENTER_FREQ}, CHAN_BW: ${CHAN_BW}"
echo "Run the following upon completion: (Automating this step in bash hasn't been working..."
echo "array_prepare_for_picoscenes "${MON_IFACE}" \"${ARR_PREP_PICO_STR}\""
