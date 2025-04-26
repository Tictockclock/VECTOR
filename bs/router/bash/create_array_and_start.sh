#!/bin/bash

device_status=$(sudo bash create_array_and_start.sh)

# Extract the numbers (e.g., 11 and 13)
numbers=$(echo "$device_status" | awk '/^[0-9]/ {print $1}')

# Assign to bash variables
number1=$(echo "$numbers" | sed -n '1p')
number2=$(echo "$numbers" | sed -n '2p')

# Print the variables (optional)
echo "Number 1: $number1"
echo "Number 2: $number2"
