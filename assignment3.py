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


# Thread to handle the client and receiving new books
def handle_client(conn, addr):
    # define global objects
    global list_head
    global connection_count
    book_head = None

    # Address connected from
    print(f"[INFO] Connected by {addr}")

    # Added connection count to function for readability
    connection_number = increment_connection_count()  # Get the current connection number
    
    previous_node = None, None # Initiliase pointers
    buffer = b''  # Buffer to accumulate data
    
    # Main while loop
    while True:
        data = conn.recv(10024)
        if not data:
            print(f"[INFO] Connection closed by {addr}")
            break
        #Accumalte lines into the buffer
        buffer, lines = accumulate_data(buffer, data)
        # Process each line, using the pointers
        if lines:
            previous_node, book_head = process_lines(lines, addr, book_head, previous_node)
    
    if books_heads[addr]:
        book_head = books_heads[addr]
    # Write book to a file when the connection closes using the connection number
    write_book_to_file(addr, connection_number, book_head)

    conn.close()
    print(f"[INFO] Connection with {addr} closed.")

# Ensure the connection count is unique for each book when connecting by locking
def increment_connection_count():
    with connection_lock:
        global connection_count
        connection_count += 1
        return connection_count

# Add data to buffer and try to decode data, if there is an error fail
def accumulate_data(buffer, data):
    buffer += data  # Accumulate data into buffer
    print(f"[DEBUG] Received {len(data)} bytes, total: {len(buffer)} bytes")

    try:
        # Try to decode the buffer, but handle incomplete data at the end
        decoded_data = buffer.decode('utf-8')
        lines = decoded_data.splitlines(keepends=True)  # Split into lines, keeping newlines
        # Check if the last line is complete (it should end with a newline character)
        if not lines[-1].endswith('\n'):
            # Incomplete last line, keep it in the buffer
            buffer = lines[-1].encode('utf-8')  # Re-encode incomplete line into buffer
            lines = lines[:-1]  # Remove the incomplete line from lines to be processed
        else:
            buffer = b''  # All lines are complete, clear the buffer
        print(f"[DEBUG] Successfully decoded {len(lines)} complete lines")
        return buffer, lines  # Return the remaining buffer and processed lines
    except UnicodeDecodeError as e:
        print(f"[WARNING] Incomplete UTF-8 sequence detected: {e}, waiting for more data")
        return buffer, []  # Return buffer and empty list if decode fails


# Add each processed line to the list
def process_lines(lines, addr, book_head, previous_node):
    global list_head
    with list_lock:
        for line in lines:
            print(f"[INFO] Processing line: {line.strip()}")
            new_node = Node(line)

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

            # Handle book linking
            if book_head is None:
                book_head = new_node
                books_heads[addr] = book_head
                print(f"[INFO] Book title detected, setting book head")
            else:
                if previous_node:
                    previous_node.book_next = new_node
                    print(f"[INFO] Linked node to book chain")

            previous_node = new_node

    return previous_node, book_head

# Write the resultant book to a file when completed.
def write_book_to_file(addr, connection_number, book_head):
    filename = f"book_{connection_number:02d}.txt"
    print(f"[INFO] Writing book to file: {filename}")
    for book in books_heads:
        print(f"[INFO] Current book heads: {book}")
    with open(filename, 'w') as book_file:
        current_node = books_heads.get(addr)
        while current_node:
            book_file.write(current_node.line)
            current_node = current_node.book_next

    print(f"[INFO] Book written to {filename}.")

# Write an analysis thread to manage the frequency analysis and output of said frequency analysis
def analysis_thread(search_pattern, interval):
    global last_output_time

    while True:
        time.sleep(interval)
        now = time.time()

        if now - last_output_time < interval:
            continue
        
        with list_lock:
            frequency_dict = count_frequencies(search_pattern)
            output_frequencies(frequency_dict)

            last_output_time = now

# Count the frequency using python defaultdict
# This covers edge cases where there is a key error if you try to access a new item not in the dictionary (defaultdict simply adds it)
def count_frequencies(search_pattern):
    frequency_dict = defaultdict(int)

    # Iterate over each book linked list in books_heads
    for addr, book in books_heads.items():  # addr is the key, book is the head of the book linked list
        current_node = book
        
        while current_node:
            line_content = current_node.line.strip()
            
            # Use regex to find the pattern in the entire line (case-insensitive)
            match_count = len(re.findall(search_pattern, line_content, re.IGNORECASE))
            
            if match_count > 0:
                frequency_dict[addr] += match_count  # Increment count for this book (by address)

            current_node = current_node.book_next  # Move to the next node in the book list
    
    return frequency_dict


# Output frequencies of each book by printing title and count
def output_frequencies(frequency_dict):
    sorted_frequencies = sorted(frequency_dict.items(), key=lambda item: item[1], reverse=True)
    print("[OUTPUT] Book Titles Sorted by Frequency of Search Pattern:")
    for title, count in sorted_frequencies:
        print(f"{books_heads[title].line.rstrip()}: {count}")

# Simple thread starter
def start_analysis_threads(search_pattern, interval, num_threads=2):
    for _ in range(num_threads):
        thread = threading.Thread(target=analysis_thread, args=(search_pattern, interval))
        thread.daemon = True
        thread.start()

# Start the server and thread handling


def start_server(port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('localhost', port))
    server.listen(5)
    print(f"Server is listening on port {port}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()


# Main function with arg parse for input 
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the server with a port and search pattern.")
    parser.add_argument('-l', '--port', type=int, required=True, help="Port number to listen on")
    parser.add_argument('-p', '--pattern', type=str, required=True, help="Pattern to search for in analysis")
    args = parser.parse_args()

    search_pattern = args.pattern
    port = args.port

    start_analysis_threads(search_pattern, interval=5)  # Start analysis threads with 5-second intervals
    start_server(port)
