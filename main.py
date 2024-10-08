import socket
import threading
import time
import sys
import argparse
import re
from collections import defaultdict

# Node class for linked list
class Node:
    def __init__(self, line):
        self.line = line
        self.next = None
        self.book_next = None
        self.next_frequent_search = None

# Shared linked list head pointers
list_head = None
books_heads = {}
list_lock = threading.Lock()
connection_count = 0  # Global variable to track connection order
connection_lock = threading.Lock()  # Lock to safely increment connection count

# Global variables
last_output_time = 0  # Tracks the last time an output occurred
output_interval = 5   # Configurable interval for output in seconds
output_lock = threading.Lock()  # Lock to synchronize output access

def handle_client(conn, addr):
    global list_head
    global connection_count
    book_head = None
    previous_node = None
    buffer = b''  # Buffer to accumulate data before decoding

    print(f"[INFO] Connected by {addr}")

    # Safely increment connection count and get the current connection number
    with connection_lock:
        connection_count += 1
        connection_number = connection_count  # Store the current connection number

    total_bytes_received = 0  # Track total bytes received

    while True:
        data = conn.recv(1024)
        if not data:
            print(f"[INFO] Connection closed by {addr}")
            break

        buffer += data  # Accumulate data into buffer
        total_bytes_received += len(data)
        print(f"[DEBUG] Received {len(data)} bytes, total: {total_bytes_received} bytes")

        try:
            # Try to decode the complete buffer
            lines = buffer.decode().splitlines(keepends=True)  # keepends=True to preserve newlines
            print(f"[DEBUG] Successfully decoded {len(lines)} lines")
            buffer = b''  # Reset buffer if decode is successful
        except UnicodeDecodeError as e:
            # If decoding fails, wait for more data (incomplete UTF-8 sequence)
            print(f"[WARNING] Incomplete UTF-8 sequence detected: {e}, waiting for more data")
            continue

        # Process each line
        for line in lines:
            print(f"[INFO] Processing line: {line.strip()}")  # Show the content of each line (without newlines)

            # Create a new node for each line
            new_node = Node(line)

            with list_lock:
                # Add node to the end of the shared list
                if list_head is None:
                    list_head = new_node
                    print(f"[INFO] Added first node to list")
                else:
                    current = list_head
                    while current.next:
                        current = current.next
                    current.next = new_node
                    print(f"[INFO] Added node to end of list")

                # If it's the first line (book title), set the head for this book
                if book_head is None:
                    book_head = new_node
                    books_heads[addr] = book_head
                    print(f"[INFO] Book title detected, setting book head")
                else:
                    # Link the nodes for this book using `book_next`
                    if previous_node:
                        previous_node.book_next = new_node
                        print(f"[INFO] Linked node to book chain")

            previous_node = new_node

    # When the connection is closed, write the book to a file
    filename = f"book_{connection_number:02d}.txt"  # Generate filename with zero-padded connection number
    print(f"[INFO] Writing book to file: {filename}")
    
    with open(filename, 'w') as book_file:
        current_node = books_heads.get(addr)
        while current_node:
            book_file.write(current_node.line)  # Write each line to the file
            current_node = current_node.book_next

    print(f"[INFO] Book written to {filename}. Total bytes received: {total_bytes_received}")

    conn.close()
    print(f"[INFO] Connection with {addr} closed.")

# Dictionary to keep track of frequency of search patterns for each book title
frequency_dict = {}

def analysis_thread(search_pattern, interval):
    global last_output_time

    while True:
        time.sleep(interval)  # Wait for the specified interval
        now = time.time()
        
        # Check if enough time has passed since the last output
        if now - last_output_time < interval:
            continue  # Skip if the output interval has not been reached
        
        with list_lock:
            # Frequency counting
            current = list_head
            frequency_dict.clear()  # Clear the previous counts

            while current:
                title = current.line.strip()
                # Count occurrences of the search pattern in the title
                match_count = len(re.findall(search_pattern, title, re.IGNORECASE))
                if match_count > 0:
                    frequency_dict[title] = frequency_dict.get(title, 0) + match_count
                current = current.next
            
            # Prepare for output
            sorted_frequencies = sorted(frequency_dict.items(), key=lambda item: item[1], reverse=True)

            # Output to stdout
            print("[OUTPUT] Book Titles Sorted by Frequency of Search Pattern:")
            for title, count in sorted_frequencies:
                print(f"{title}: {count}")

            # Update the last output time
            last_output_time = now


def start_analysis_threads(search_pattern, interval, num_threads=2):
    for i in range(num_threads):
        thread = threading.Thread(target=analysis_thread, args=(search_pattern, interval))
        thread.daemon = True  # Make the thread a daemon so it terminates when the main program does
        thread.start()

def start_server(port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('localhost', port))
    server.listen(5)
    print(f"Server is listening on port {port}")
    
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Start the server with a port and search pattern.")
    parser.add_argument('-l', '--port', type=int, required=True, help="Port number to listen on")
    parser.add_argument('-p', '--pattern', type=str, required=True, help="Pattern to search for in analysis")
    args = parser.parse_args()

    search_pattern = args.pattern
    port = args.port

    # Start analysis threads
    start_analysis_threads(search_pattern, interval=5)  # Start analysis threads with 5-second intervals
    # Start server
    start_server(port)
