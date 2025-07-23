import socket
import json
import threading
from ctransformers import AutoModelForCausalLM

HOST = 'localhost'
PORT = 5000
SUCCESS_CODE = 200
MESSAGE_TYPE_ERROR = 400
NO_CASE_ERROR = 401
PROMPT_PARSE_ERROR = 402

cases = ""

def get_commands(message, llm):
    try:
        data = json.loads(message)
        print(f"receive request: {message}")
        request_id = data.get("request_id")
        temperature = data.get("temperature")
        humidity = data.get("humidity")
        lightIntensity = data.get("lightIntensity")
        fan_speed = data.get("fan")
        prompt = f'''
        ### Instruction:
        This is an micro-climate sensor data over 15 minutes (1 reading per minute per sensor).
        The sensor reports temperature (°C), humidity (%RH), and light intensity (lux).

        Please find out which case the environment is now and output the control commands in response.
        Example response format:
        {{"fan": 1500, "led": 2000}}

        ### Environment Data:
        temperature: {temperature}
        humidity: {humidity}
        light intensity: {lightIntensity}
        
        ### Cases
        {str(cases)}
        
        Case_ID: The edition of case
        Condition_IF: Condition of case
        Diagnosis_Tradeoff_Analysis: Diagnosis tradeoff analysis of case
        Primary_Control_Priority: Primary control priority of case
        Prioritized_Action_Chain: Control commands, which you should output in response
        15 min_Goal_and_Tradeoff: Goal and Tradeoff in next 15 minutes
        
        ### Response:

        '''
        command = json.loads(llm(prompt))
        command["response_id"] = request_id

        return json.dumps(command)

    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"})

def process_prompt(message):
    global cases

    data = json.loads(message)
    response = {"request_id": data["type"]}
    cases = data.get("cases")

    if cases:
        response["code"] = SUCCESS_CODE
        return response
    else:
        response["code"] = PROMPT_PARSE_ERROR
        return response


def handle_client(conn, addr):
    print(f"client {addr} connecting")
    try:
        message = conn.recv(4096).decode()
        if message:
            data = json.loads(message)
            if data["type"] == 0:
                response = get_commands(data, llm)
            elif data["type"] == 1:
                response = process_prompt(data)
            else:
                response = {"request_id": data["type"], "code": MESSAGE_TYPE_ERROR}
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
    run_server()
