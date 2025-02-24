import zmq
import argparse
import os

SERVER_HOST = 'localhost'
SERVER_PORT = 12346  # Updated to match the ZeroMQ file server port

def send_file(file_path):
    """
    Sends the full and complete file
    @param file_path: the path to the file to be sent
    """
    context = zmq.Context()
    socket = context.socket(zmq.PUSH)
    socket.setsockopt(zmq.LINGER, 0)  # Set linger to zero to close the socket immediately
    socket.connect(f"tcp://{SERVER_HOST}:{SERVER_PORT}")

    filename = os.path.basename(file_path)
    print(f"Sending file {file_path} to {SERVER_HOST}:{SERVER_PORT}...")

    socket.send_string(filename)  # Send the filename first

    with open(file_path, "rb") as f:
        while chunk := f.read(1024):  # Read file in 1024-byte chunks
            socket.send(chunk)

    socket.send(b"EOF")  # Send End of File marker
    print("File sent successfully.")
    socket.close()
    context.term()

def send_udp_message(message):
    """
    Sends a one-sided message to the server
    @param message: the message to be sent
    """
    context = zmq.Context()
    socket = context.socket(zmq.PUSH)
    socket.setsockopt(zmq.LINGER, 0)  # Set linger to zero to close the socket immediately
    socket.connect(f"tcp://{SERVER_HOST}:{SERVER_PORT + 1}")  # Different port for messages

    print(f"Sending message to {SERVER_HOST}:{SERVER_PORT + 1}...")
    socket.send_string(message)
    print("Message sent successfully.")
    socket.close()
    context.term()

def parser_setup():
    parser = argparse.ArgumentParser(description="Client to send files or messages to the server.")
    parser.add_argument('-s', '--send', type=str, help="Path to the file to send")
    parser.add_argument('-m', '--message', type=str, help="Message to send")
    args = parser.parse_args()

    if args.send:
        send_file(args.send)
    elif args.message:
        send_udp_message(args.message)
    else:
        print("Please provide a file to send or a message to send.")

if __name__ == "__main__":
    parser_setup()