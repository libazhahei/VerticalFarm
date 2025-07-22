import pytest
from fastapi.testclient import TestClient
from backend_main import app
from route.utils import GlobalContext, RunningMode

client = TestClient(app)

def test_read_index():
    response = client.get("/", follow_redirects=False)
    # Should redirect to /docs
    assert response.status_code in (302, 307)
    assert response.headers["location"].endswith("/docs")

def test_get_devices(monkeypatch):
    class DummyMQTTService:
        async def alive_devices(self):
            return [1, 2]

    class DummyWriter:
        async def fetch_latest(self, devices):
            class DummyData:
                def __init__(self, board_id, timestamp):
                    self.board_id = board_id
                    self.timestamp = type('ts', (), {'timestamp': lambda self: timestamp})()
            return [DummyData(1, 1234567890), DummyData(2, 1234567891)]

    class DummyContext:
        mqtt_service_context = DummyMQTTService()
        ble_service_context = True

    monkeypatch.setattr('route.utils.GlobalContext.get_instance', lambda: DummyContext())
    monkeypatch.setattr('data.tables.BoardDataBatchWriter.get_instance', lambda: DummyWriter())

    response = client.get('/devices')
    assert response.status_code == 200
    assert 'devices' in response.json()
    assert len(response.json()['devices']) == 2
    assert response.json()['devices'][0]['board_id'] == 1
    assert response.json()['devices'][1]['board_id'] == 2


# You can add more tests for other routes if needed

import asyncio
from unittest.mock import AsyncMock


def test_get_human_task(monkeypatch):
    class DummyLLMCache:
        async def access(self, func, default=None):
            return [['Check', 'Do']]  # list of lists
    monkeypatch.setattr('llm.cloud.CloudLLMCache.get_instance', AsyncMock(return_value=DummyLLMCache()))
    response = client.get('/api/ai/human_task')
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_verification(monkeypatch):
    class DummyLLMCache:
        async def access(self, func, default=None):
            return [
                {
                    'condition': 'cond',
                    'detection_period': 'period',
                    'equipment_limitation_considered': True,
                    'location_season_weather_considered': True,
                    'recovery_suggestion': 'suggest'
                }
            ]
    monkeypatch.setattr('llm.cloud.CloudLLMCache.get_instance', AsyncMock(return_value=DummyLLMCache()))
    response = client.get('/api/ai/verification')
    assert response.status_code == 200
    assert isinstance(response.json(), list)

# --- History routes ---
def test_get_temperature_history(monkeypatch):
    class DummyWriter:
        async def fetch_since(self, since, board_ids=None):
            class DummyData:
                board_id = 1
                timestamp = since
                temperature = 25.0
            return [DummyData()]
    monkeypatch.setattr('data.tables.BoardDataBatchWriter.get_instance', lambda: DummyWriter())
    payload = {'unit': 'min', 'start_from': 0}
    response = client.post('/ap/history/temperature', json=payload)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_humidity_history(monkeypatch):
    class DummyWriter:
        async def fetch_since(self, since, board_ids=None):
            class DummyData:
                board_id = 1
                timestamp = since
                humidity = 60.0
            return [DummyData()]
    monkeypatch.setattr('data.tables.BoardDataBatchWriter.get_instance', lambda: DummyWriter())
    payload = {'unit': 'min', 'start_from': 0}
    response = client.post('/ap/history/humidity', json=payload)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_light_history(monkeypatch):
    class DummyWriter:
        async def fetch_since(self, since, board_ids=None):
            class DummyData:
                board_id = 1
                timestamp = since
                light_intensity = 1000
            return [DummyData()]
    monkeypatch.setattr('data.tables.BoardDataBatchWriter.get_instance', lambda: DummyWriter())
    payload = {'unit': 'min', 'start_from': 0}
    response = client.post('/ap/history/light', json=payload)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

# --- Others routes ---
def test_get_realtime_data(monkeypatch):
    class DummyWriter:
        boards_ids = [1]
        async def fetch_latest(self, ids):
            class DummyData:
                temperature = 25.0
                humidity = 60.0
                light_intensity = 1000
                timestamp = type('ts', (), {'timestamp': lambda self: 1234567890})()
            return {1: DummyData()}
    monkeypatch.setattr('data.tables.BoardDataBatchWriter.get_instance', lambda: DummyWriter())
    response = client.get('/api/realtime')
    assert response.status_code == 200
    assert 'boards' in response.json()

def test_get_board_status(monkeypatch):
    class DummyWriter:
        boards_ids = [1]
        async def fetch_latest(self, ids):
            class DummyData:
                board_id = 1
                temperature = 25.0
                humidity = 60.0
                light_intensity = 1000
                timestamp = type('ts', (), {'timestamp': lambda self: 1234567890})()
            return [DummyData()]
    monkeypatch.setattr('data.tables.BoardDataBatchWriter.get_instance', lambda: DummyWriter())
    response = client.get('/api/board/1/status')
    assert response.status_code == 200
    assert 'temperature' in response.json() or 'error' in response.json()

# --- Control routes ---
def test_control_board():
    response = client.get('/api/control/1')
    assert response.status_code == 200
    assert 'mode' in response.json()
    assert response.json()['mode'] in ['auto']

def test_update_board(monkeypatch):
    
    # Mocking the MQTT service context
    class DummyMQTTService:
        async def publish_control_command(self, msg):
            return True
    # Use mock mqtt service in GlobalContext
    class DummyContext:
        mqtt_service_context = DummyMQTTService()
        running_mode = 'manual'
        running_target = {}

        async def switch_running_mode(self, mode, target=None):
            pass

    monkeypatch.setattr('route.utils.GlobalContext.get_instance', lambda: DummyContext())
    payload = {
        'running_mode': RunningMode.MANUAL,
        'temperature': 25.0,
        'light_intensity': 100.0,
        'humidity': 50.0
    }
    response = client.post('/api/control/1', json=payload)
    assert response.status_code == 200
    assert 'mode' in response.json()
    assert response.json()['mode'] == 'manual'
