import socket
import json
import uuid
import cloud

SERVER_IP = 'localhost'
SERVER_PORT = 5000

# TODO: all data come from database, need to finish
request = {"request_id": str(uuid.uuid4()),
               "temperature": [],
               "humidity": [],
               "lightIntensity": [],
               "fan": 90,
               "led": 150}

# arguments: data: json
def request_for_commands(data, prompt):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVER_IP, SERVER_PORT))
        s.sendall(json.dumps(data).encode())
        response = s.recv(4096).decode()
        print("command received：", response)

def send_prompt(prompt):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVER_IP, SERVER_PORT))
        s.sendall(json.dumps(prompt).encode())
        response = s.recv(4096).decode()
        print("command received：", response)
