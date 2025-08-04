# VerticalFarm

## How to Run FastAPI

To run the FastAPI application, follow these steps:

1. **Install Dependencies**:
    Ensure you have Python installed. Install the required dependencies from the `requirements.txt` file using pip:
    ```bash
    pip install -r requirements.txt
    pip install fastapi[standard]
    ```

2. **Run the Application**:
    Use the following command to start the FastAPI server using the FastAPI CLI:
    ```bash
    fastapi dev backend_main.py
    ```
    Replace `main` with the name of your Python file containing the FastAPI app.

3. **Access the Application**:
    Open your browser and navigate to `http://127.0.0.1:8000` to access the application.

4. **API Documentation**:
    FastAPI automatically generates interactive API documentation:
    - Swagger UI: `http://127.0.0.1:8000/docs`
    - ReDoc: `http://127.0.0.1:8000/redoc`

5. **Stopping the Server**:
    Press `Ctrl+C` in the terminal to stop the server.
