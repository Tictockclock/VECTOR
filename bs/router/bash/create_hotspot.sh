#!/bin/bash

#sudo systemctl stop NetworkManager
#sudo systemctl stop systemd-networkd

# Function to detect the first Wi-Fi interface (starting with 'wlp')
get_wifi_interface() {
    # List all network devices, filter for Wi-Fi interfaces, and pick the first one
    INTERFACE=$(nmcli device status | grep -o 'wlp[^ ]*' | head -n 1)

    # Check if we found a Wi-Fi interface
    if [ -z "$INTERFACE" ]; then
        echo "No Wi-Fi interface found. Make sure a Wi-Fi card is installed."
        exit 1
    fi

    echo $INTERFACE
}
# sudo systemctl enable NetworkManager
# sudo systemctl start NetworkManager
# sudo systemctl restart NetworkManager

sleep 5

# Get the Wi-Fi interface dynamically
INTERFACE=$(get_wifi_interface)

# Default values (you can modify these as needed)
CHANNEL=6                   # Channel for the hotspot
PASSWORD="YourPassword123"  # WPA2 password
CONFIG_PATH="/etc/hostapd/hostapd.conf"  # Path to the hostapd config file
SSID = ""
# Check if user is running as root (required to modify /etc/hostapd)
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root."
    exit 1
fi

# Create or overwrite the hostapd.conf file
echo "Creating or modifying $CONFIG_PATH..."
echo $INTERFACE
cat > $CONFIG_PATH <<EOL
interface=$INTERFACE
driver=nl80211
ssid=$SSID
hw_mode=g
channel=$CHANNEL
ieee80211n=1
wmm_enabled=1
auth_algs=1
wpa=2
wpa_key_mgmt=WPA-PSK
wpa_passphrase=$PASSWORD
rsn_pairwise=CCMP
EOL

echo "hostapd.conf file created at $CONFIG_PATH."

# Optionally restart hostapd service or run hostapd to apply the configuration
# sudo systemctl restart hostapd  # Uncomment if hostapd service is installed and enabled

# Run hostapd manually to apply the config
echo "Attempting to start hostapd with the new configuration..."
sudo hostapd $CONFIG_PATH

echo "Configuration file setup complete. You can start hostapd manually if needed."
nmcli device wifi hotspot ifname wlp3s0 con-name MyHotspot ssid MyHotspotNetwork password "YourPassword123"