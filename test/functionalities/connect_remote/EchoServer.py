#!/usr/bin/env python 

""" 
A simple echo server.
Taken from http://docs.python.org/library/socket.html#example.
"""

import socket

HOST = 'localhost'        # Symbolic name meaning local interfaces
PORT = 0                  # Let the system give us a random free port
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
PORT = s.getsockname()[1]
print 'Listening on %s:%d' % (HOST, PORT)
s.listen(1)
conn, addr = s.accept()
print 'Connected by', addr
while 1:
    data = conn.recv(1024)
    if data: 
        print 'Received:', data
        # Don't response to acks that are sent to us
        if data != '+':
            conn.send("+$#00")
    else:
        break
conn.close()
