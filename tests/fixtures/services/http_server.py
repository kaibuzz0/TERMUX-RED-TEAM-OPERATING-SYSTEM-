#!/usr/bin/env python3
"""Tiny loopback HTTP server for tests."""

import argparse
import socket


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("host", default="127.0.0.1")
    parser.add_argument("port", type=int, default=0)
    args = parser.parse_args()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((args.host, args.port))
    addr = server.getsockname()
    server.listen(1)
    print(f"listening {addr[1]}", flush=True)
    try:
        while True:
            conn, _ = server.accept()
            conn.recv(1024)
            conn.sendall(b"HTTP/1.1 200 OK\r\n\r\nok")
            conn.close()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
