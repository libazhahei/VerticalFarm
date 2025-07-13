import openai

system_prompt = """
You are an intelligent assistant specializing in environmental monitoring for indoor vertical farms.
Based on the provided daily sensor data, please generate a structured report with the following sections:

1. Summary Statistics: Average, min, and max values for temperature, humidity, and light (PAR).
2. Anomaly Detection: Identify any high-temperature (>30°C), low-humidity (<50%), or low-light (<100 PAR) conditions, along with affected sensor IDs and time ranges.
3. Recommended Actions: Suggest control adjustments (e.g., fan speed, humidity level, LED intensity) to correct problems.
4. Overall Assessment: Evaluate whether the farm's environment is healthy or needs manual intervention.

Format the output in clear sections with bullet points or labels.
"""

user_prompt = "Please analyze the attached sensor data and generate a report including summary statistics, anomaly detection, recommended control actions, and overall farm status"

def get_daily_report():
    # upload file
    # TODO: generate daily sensor data file
    file_response = openai.files.create(
        file=open("fake_data.csv", "rb"),
        purpose="assistants"
    )
    print("Uploaded file:", file_response.id)

    # send the request to GPT-4o
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        file_ids=[file_response.id],
        temperature=0.4
    )

    return response["choices"][0]["message"]["content"]
