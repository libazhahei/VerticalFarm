import socket
import json
import uuid
import cloud
import pandas as pd

SERVER_IP = 'localhost'
SERVER_PORT = 5000
GET_COMMAND = 0
SEND_PROMPT = 1

def build_request(file):
    df = pd.read_csv(file)
    temp = df['temperature'].mean()
    light = df['light'].mean()
    fan = df['fan_speed'].mean()
    humidity = df['humidity'].mean()
    request = {"request_id": uuid.uuid4(),
               "type": GET_COMMAND,
               "temperature": temp,
               "humidity": humidity,
               "lightIntensity": light,
               "fan": fan}
    return request

# arguments: data: json
def request_for_commands(file):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVER_IP, SERVER_PORT))
        request = build_request("ble_data.csv")
        s.sendall(json.dumps(request).encode())
        response = json.loads(s.recv(4096).decode())
        if response.get("request_id") == request.get("request_id") and response.get("code") == 200:
            print("command received：", response)
            return response
        else:
            print(f"Error {response.get("code")}")
            return None

def build_prompt(prompt) -> json:
    prompt["request_id"] = uuid.uuid4()
    prompt["type"] = SEND_PROMPT
    return prompt

def send_prompt(prompt):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVER_IP, SERVER_PORT))
        request = build_prompt(prompt)
        s.sendall(json.dumps(request).encode())
        response = json.loads(s.recv(4096).decode())
        if response.get("request_id") == request.get("request_id") and response.get("status") == 200:
            print("prompt send success：", response)
            return True
        else:
            print(f"Error {response.get("code")}")
            return False


