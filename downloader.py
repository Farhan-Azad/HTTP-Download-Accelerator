#!/usr/bin/env python3
import sys
import socket
import threading
from urllib.parse import urlparse


def parse_http_response(data):
    """Extract headers from HTTP response"""
    header_end = data.find(b'\r\n\r\n')
    if header_end == -1:
        return None, None

    headers_section = data[:header_end].decode('utf-8', errors='ignore')
    body = data[header_end + 4:]

    headers = {}
    lines = headers_section.split('\r\n')

    for line in lines[1:]:  # Skip status line
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip().lower()] = value.strip()

    return headers, body


def send_http_request(host, port, request):
    """Send HTTP request and return full response"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    sock.sendall(request.encode('utf-8'))

    response = b''
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response += chunk

    sock.close()
    return response


def get_content_length(host, port, path):
    """Send HEAD request to get file size"""
    request = f"HEAD {path} HTTP/1.0\r\n"
    request += f"Host: {host}\r\n"
    request += "Connection: close\r\n"
    request += "\r\n"

    response = send_http_request(host, port, request)
    headers, _ = parse_http_response(response)

    if headers and 'content-length' in headers:
        return int(headers['content-length'])

    return None


def download_range(host, port, path, start, end, filename, thread_id):
    """Download a specific byte range and write to file"""
    request = f"GET {path} HTTP/1.0\r\n"
    request += f"Host: {host}\r\n"
    request += f"Range: bytes={start}-{end}\r\n"
    request += "Connection: close\r\n"
    request += "\r\n"

    print(f"Thread {thread_id}: Downloading bytes {start}-{end}")

    response = send_http_request(host, port, request)
    headers, body = parse_http_response(response)

    # Write to the correct position in the file
    with open(filename, 'r+b') as f:
        f.seek(start)
        f.write(body)

    print(f"Thread {thread_id}: Completed")


def main():
    if len(sys.argv) != 4:
        print("Usage: python downloader.py NumberOfThreads ObjectURI localFilename")
        sys.exit(1)

    try:
        num_threads = int(sys.argv[1])
    except ValueError:
        print("Error: NumberOfThreads must be an integer")
        sys.exit(1)

    if num_threads < 1 or num_threads > 16:
        print("Error: NumberOfThreads must be between 1 and 16")
        sys.exit(1)

    object_uri = sys.argv[2]
    local_filename = sys.argv[3]

    # Parse the URL
    parsed = urlparse(object_uri)
    host = parsed.hostname
    port = parsed.port if parsed.port else 80
    path = parsed.path if parsed.path else '/'

    if not host:
        print("Error: Invalid URI")
        sys.exit(1)

    print(f"Downloading {object_uri}")
    print(f"Host: {host}, Port: {port}, Path: {path}")

    # Get file size using HEAD request
    content_length = get_content_length(host, port, path)

    if content_length is None:
        print("Error: Could not determine file size")
        sys.exit(1)

    print(f"File size: {content_length} bytes")

    # Create empty file with the right size
    with open(local_filename, 'wb') as f:
        f.write(b'\0' * content_length)

    # Calculate byte ranges for each thread
    chunk_size = content_length // num_threads
    threads = []

    for i in range(num_threads):
        start = i * chunk_size

        # Last thread gets any remaining bytes
        if i == num_threads - 1:
            end = content_length - 1
        else:
            end = start + chunk_size - 1

        thread = threading.Thread(
            target=download_range,
            args=(host, port, path, start, end, local_filename, i + 1)
        )
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    print(f"Download complete: {local_filename}")


if __name__ == "__main__":
    main()