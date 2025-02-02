import socket

def send_udp_message(message, host='127.0.0.1', port=12345):
    # Create a UDP socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Send the message to the server
    client_socket.sendto(message.encode('utf-8'), (host, port))

    # Close the socket immediately
    client_socket.close()

if __name__ == "__main__":
    for i in range(0, 33):
        send_udp_message(f"Hello, UDP Server!{i}")