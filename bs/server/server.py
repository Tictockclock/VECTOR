import socket

def start_udp_server(host='127.0.0.1', port=12345):
    # Create a UDP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Bind the socket to the address and port
    server_socket.bind((host, port))

    print(f"UDP server listening on {host}:{port}")

    try:
        while True:
            # Receive data from the client
            data, client_address = server_socket.recvfrom(4096)
            print(f"Received data from {client_address}: {data.decode('utf-8')}")

            # Process the data (for example, convert to uppercase)
            response = data.upper()

            # Send the response back to the client
            server_socket.sendto(response, client_address)
            print(f"Sent response to {client_address}: {response.decode('utf-8')}")

    except KeyboardInterrupt:
        print("Server is shutting down...")
    finally:
        # Close the socket
        server_socket.close()
        print("Server socket closed.")

if __name__ == "__main__":
    start_udp_server()