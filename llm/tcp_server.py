import socket
import json
import threading
from ctransformers import AutoModelForCausalLM

HOST = 'localhost'
PORT = 5000

def get_commands(message, llm):
    try:
        data = json.loads(message)
        print(f"receive request: {message}")
        request_id = data.get("request_id")
        temperature = data.get("temperature")
        humidity = data.get("humidity")
        lightIntensity = data.get("lightIntensity")
        fan_speed = data.get("fan")
        led = data.get("led")
        prompt = f'''
        ### Instruction:
        This is an micro-climate sensor data over 15 minutes (1 reading per minute per sensor).
        The sensor reports temperature (°C), humidity (%RH), and light intensity (PAR µmol/m²/s).

        Please identify if the climate is too hot (avg temp > 30°C), too dry (avg RH < 50%), or underlit (avg PAR < 100).
        The current fan speed and led brightness are {{"fan": {fan_speed}, "led": {led}}}
        If the climate is too hot, increase the fan speed; otherwise, decrease it.
        If the climate is too dry, decrease the LED brightness. otherwise, increase it.
        If the climate is underlit, increase the LED brightness. otherwise, decrease it.
        Return a JSON control command to adjust fan (range: 0-255) and LED (range: 0-255) accordingly.

        Example response format:
        {{"fan": 90, "led": 30}}

        ### Data:

        temperature: {temperature}
        humidity: {humidity}
        light intensity: {lightIntensity}

        ### Response:

        '''
        command = json.loads(llm(prompt))
        command["response_id"] = request_id

        return json.dumps(command)

    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"})

def handle_client(conn, addr):
    print(f"client {addr} connecting")
    try:
        data = conn.recv(1024).decode()
        if data:
            response = get_commands(data, llm)
            conn.sendall(response.encode())
    except Exception as e:
        print(f"client {addr} error：{e}")
    finally:
        conn.close()
        print(f"client {addr} disconnected")
def run_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((HOST, PORT))
        server.listen()
        print(f"server running on {HOST}:{PORT}...")

        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()

if __name__ == "__main__":
    llm = AutoModelForCausalLM.from_pretrained(
        "TheBloke/Llama-2-7b-Chat-GGUF",
        model_file="llama-2-7b-chat.Q5_K_M.gguf",
        model_type="llama",
        context_length=1024,
        gpu_layers=50
    )
