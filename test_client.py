import os
import socket
import threading
import selectors

# Define the folder containing the text files
folder_path = 'test_books'

# Initialize the default selector
sel = selectors.DefaultSelector()

def send_file_contents_nonblocking(file_path):
    """Send the contents of a file over a non-blocking TCP socket."""
    try:
        # Create a TCP/IP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)  # Set socket to non-blocking mode

        # Connect to the server (non-blocking connect)
        try:
            sock.connect(('localhost', 1234))
        except BlockingIOError:
            pass  # Connection will be established later, handled by the selector

        # Register the socket for writing
        sel.register(sock, selectors.EVENT_WRITE, data=file_path)

        def send_data(sock):
            with open(file_path, 'r') as file:
                content = file.read()
                # Send the file content
                sock.sendall(content.encode('utf-8'))
                print(f"Sent: {file_path}")
                sel.unregister(sock)
                sock.close()

        sel.modify(sock, selectors.EVENT_WRITE, send_data)

    except Exception as e:
        print(f"Error sending {file_path}: {e}")

def process_events():
    """Process events from the selector."""
    while True:
        events = sel.select(timeout=0)
        for key, mask in events:
            callback = key.data
            if callable(callback):
                callback(key.fileobj)

def main():
    # Create and start a thread to process events
    event_thread = threading.Thread(target=process_events, daemon=True)
    event_thread.start()

    # Iterate through the files in the specified folder
    for filename in os.listdir(folder_path):
        if filename.endswith('.txt') or filename.endswith('.utf-8'):
            file_path = os.path.join(folder_path, filename)
            send_file_contents_nonblocking(file_path)

if __name__ == '__main__':
    main()
