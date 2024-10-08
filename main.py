import socket
import threading
import time
import sys
import argparse

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

def handle_client(conn, addr):
    global list_head
    book_head = None
    previous_node = None
    buffer = b''  # Buffer to accumulate data before decoding

    print(f"[INFO] Connected by {addr}")
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

    # Print the book after receiving all data
    print(f"[INFO] Printing the book for {addr}...")
    current_node = books_heads.get(addr)
    while current_node:
        print(current_node.line, end='')  # Print each line, end='' to avoid double newlines
        current_node = current_node.book_next

    conn.close()
    print(f"[INFO] Connection with {addr} closed. Total bytes received: {total_bytes_received}")


def analysis_thread(search_pattern, interval):
    while True:
        time.sleep(interval)  # Periodically check every `interval` seconds
        pattern_count = {}
        print(f"[INFO] Analysis thread is searching for pattern '{search_pattern}'...")

        with list_lock:
            for addr, book_head in books_heads.items():
                count = 0
                current_node = book_head
                while current_node:
                    if search_pattern in current_node.line:  # Fix: Use current_node.line
                        count += 1
                    current_node = current_node.book_next

                # Store count for each book (by address)
                pattern_count[addr] = count

        # Sort by the highest frequency and print the results
        sorted_books = sorted(pattern_count.items(), key=lambda x: x[1], reverse=True)
        print(f"[INFO] Pattern '{search_pattern}' frequency analysis:")

        for addr, count in sorted_books:
            print(f"[INFO] Book from {addr}: {count} occurrences")

        print(f"[INFO] Finished analysis for this interval.")


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
