import socket
import time

HOST = '127.0.0.1'
PORT = 8080

def test_plc():
    print(f"Connecting to {HOST}:{PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print("Connected.")
        
        # Test string: 042 + 1000 + 00123 + 123456789
        msg = "042100000123123456789"
        print(f"Sending: {msg}")
        s.sendall(msg.encode('utf-8'))
        
        data = s.recv(1024)
        print(f"Received: {data.decode('utf-8')}")

if __name__ == "__main__":
    test_plc()
