#!/bin/bash

# Get a list of IP addresses of connected users, excluding those on tty2
users_ips=$(who | grep -v 'tty2' | awk '{print $5}' | sed 's/[()]//g' | sort | uniq)

# If no users are connected, exit
if [ -z "$users_ips" ]; then
  echo "No users are currently connected."
  exit 1
fi

# Ping each connected user
echo "Pinging the following IPs: $users_ips"

for ip in $users_ips; do
  echo "Pinging $ip..."
  ping -c 1 -w 5 $ip &> /dev/null
  if [ $? -eq 0 ]; then
    echo "$ip is reachable."
  else
    echo "$ip is unreachable."
  fi
done
