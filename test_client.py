import os
import socket
import threading

# Define the folder containing the text files
folder_path = 'test_books'

def send_file_contents(file_path):
    """Send the contents of a file over TCP socket."""
    try:
        # Create a TCP/IP socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # Connect the socket to the server
            sock.connect(('localhost', 1234))
            with open(file_path, 'r') as file:
                content = file.read()
                # Send the file content
                sock.sendall(content.encode('utf-8'))
                print(f"Sent: {file_path}")
    except Exception as e:
        print(f"Error sending {file_path}: {e}")

def main():
    threads = []

    # Iterate through the files in the specified folder
    for filename in os.listdir(folder_path):
        if filename.endswith('.txt') or filename.endswith('.utf-8'):
            file_path = os.path.join(folder_path, filename)
            # Create a new thread for each file
            thread = threading.Thread(target=send_file_contents, args=(file_path,))
            threads.append(thread)
            thread.start()  # Start the thread

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

if __name__ == '__main__':
    main()
