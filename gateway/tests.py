import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock, call
import sys
import types
import builtins
from .msg import ControlMsg, HeartbeatMsg, StatusMsg, Mode, Status
from .publisher import ControlCommandPublisher
from .service import MqttClientWrapper, MQTTServiceContext

# Patch constants and paho.mqtt.client before imports
sys.modules['paho'] = types.ModuleType('paho')
sys.modules['paho.mqtt'] = types.ModuleType('paho.mqtt')
sys.modules['paho.mqtt.client'] = types.ModuleType('paho.mqtt.client')
setattr(sys.modules['paho.mqtt.client'], 'Client', MagicMock())
setattr(sys.modules['paho.mqtt.client'], 'MQTTMessage', MagicMock())
setattr(sys.modules['paho.mqtt.client'], 'MQTT_ERR_SUCCESS', 0)

# Patch constants
builtins.__dict__['PUBLISH_ERR_MAX_RETRIES'] = 2
builtins.__dict__['PUBLISH_CTRL_QOS'] = 1
builtins.__dict__['PUBLISH_RESENT_MAX_RETRIES'] = 2
builtins.__dict__['PUBLISH_TIMEOUT_SECONDS'] = 0.1
builtins.__dict__['SUBSCRIBE_HEARTBEAT_TIMEOUT_SECONDS'] = 2
builtins.__dict__['SUBSCRIBE_HEARTBEAT_TOPIC'] = "heartbeat"
builtins.__dict__['SUBSCRIBE_CTRL_MSG_TOPIC'] = "ctrl"

from .subscriber import (
    HeartbeatSubscriber, CommandResponseSubscriber, MessageDispatcher
)

@pytest.mark.asyncio
async def test_control_command_publisher_add_msg_and_acknowledge(monkeypatch):
    mqtt_client = MagicMock()
    is_alive_func = AsyncMock(return_value=True)
    publisher = ControlCommandPublisher(mqtt_client, is_alive_func)
    msg = ControlMsg(board_id=1, fan=10, led=20, temperature=25.0, light_intensity=50.0)
    monkeypatch.setattr(publisher, "safe_publish", lambda m, t: True)
    task = asyncio.create_task(publisher.add_msg(msg, "ctrl"))
    await asyncio.sleep(0.05)
    publisher.acknowledge(msg.get_message_id())
    await asyncio.sleep(0.05)
    assert msg.get_message_id() not in publisher.msgs

@pytest.mark.asyncio
async def test_control_command_publisher_add_msg_type_error():
    mqtt_client = MagicMock()
    is_alive_func = AsyncMock(return_value=True)
    publisher = ControlCommandPublisher(mqtt_client, is_alive_func)
    with pytest.raises(TypeError):
        await publisher.add_msg(StatusMsg(1, Status.WARNING), "ctrl")

@pytest.mark.asyncio
async def test_control_command_publisher_try_publish_timeout(monkeypatch):
    mqtt_client = MagicMock()
    is_alive_func = AsyncMock(return_value=True)
    publisher = ControlCommandPublisher(mqtt_client, is_alive_func, max_retries=1, timeout=0.01)
    msg = ControlMsg(board_id=1, fan=10, led=20, temperature=25.0, light_intensity=50.0)
    monkeypatch.setattr(publisher, "safe_publish", lambda m, t: True)
    await publisher.add_msg(msg, "ctrl")
    await asyncio.sleep(0.05)
    assert msg.get_message_id() not in publisher.msgs

@pytest.mark.asyncio
async def test_control_command_publisher_try_publish_device_not_alive(monkeypatch):
    mqtt_client = MagicMock()
    is_alive_func = AsyncMock(return_value=False)
    publisher = ControlCommandPublisher(mqtt_client, is_alive_func)
    msg = ControlMsg(board_id=1, fan=10, led=20, temperature=25.0, light_intensity=50.0)
    monkeypatch.setattr(publisher, "safe_publish", lambda m, t: True)
    await publisher.add_msg(msg, "ctrl")
    await asyncio.sleep(0.05)
    assert msg.get_message_id() not in [msg.payload.get_message_id() for msg in publisher.msgs.values()]

def test_control_command_publisher_safe_publish_success():
    mqtt_client = MagicMock()
    mqtt_client.publish.return_value.rc = 0
    is_alive_func = AsyncMock()
    publisher = ControlCommandPublisher(mqtt_client, is_alive_func)
    msg = ControlMsg(board_id=1, fan=10, led=20, temperature=25.0, light_intensity=50.0)
    assert publisher.safe_publish(msg, "ctrl")

def test_control_command_publisher_safe_publish_failure():
    mqtt_client = MagicMock()
    mqtt_client.publish.return_value.rc = 1
    is_alive_func = AsyncMock()
    publisher = ControlCommandPublisher(mqtt_client, is_alive_func)
    msg = ControlMsg(board_id=1, fan=10, led=20, temperature=25.0, light_intensity=50.0)
    assert not publisher.safe_publish(msg, "ctrl")

@pytest.mark.asyncio
async def test_heartbeat_subscriber_handle_and_is_alive():
    sub = HeartbeatSubscriber()
    msg = HeartbeatMsg(board_id=2, seq_no=123)
    await sub.handle(msg)
    assert await sub.is_alive(2)
    assert 2 in await sub.get_alive_devices()

@pytest.mark.asyncio
async def test_heartbeat_subscriber_parse_json():
    msg = HeartbeatMsg(board_id=1, seq_no=99)
    json_str = '{"boardID": 1, "seqNo": 99}'
    parsed = HeartbeatSubscriber.parse_json(json_str)
    assert parsed.board_id == msg.board_id
    assert parsed.seq_no == msg.seq_no

@pytest.mark.asyncio
async def test_command_response_subscriber_handle_and_parse_json():
    called = []
    def ack_func(board_id):
        called.append(board_id)
    sub = CommandResponseSubscriber(ack_func)
    msg = StatusMsg(message_id=1, board_id=3, status=Status.OK, timestamp=1.0)
    await sub.handle(msg)
    assert called == [3]
    json_str = '{"messageID": 1, "boardID": 3, "status": 0, "timestamp": 1.0}'
    parsed = CommandResponseSubscriber.parse_json(json_str)
    assert parsed.board_id == 3

@pytest.mark.asyncio
async def test_message_dispatcher_register_and_dispatch():
    dispatcher = MessageDispatcher()
    called = []
    async def handler(msg):
        called.append(msg)
    dispatcher.register_handler(ControlMsg, handler)
    msg = ControlMsg(board_id=1, fan=10, led=20, temperature=25.0, light_intensity=50.0)
    await dispatcher.dispatch(msg)
    assert called and isinstance(called[0], ControlMsg)

@pytest.mark.asyncio
async def test_message_dispatcher_loop(monkeypatch):
    dispatcher = MessageDispatcher()
    called = []
    async def handler(msg):
        called.append(msg)
    dispatcher.register_handler(ControlMsg, handler)
    await dispatcher.start()
    msg = ControlMsg(board_id=1, fan=10, led=20, temperature=25.0, light_intensity=50.0)
    await dispatcher.put_message(msg)
    await asyncio.sleep(0.1)
    await dispatcher.stop()
    assert called

def test_mqtt_client_wrapper_register_topic_handler_and_connect(monkeypatch):
    dispatcher = MagicMock()
    mqtt_client = MagicMock()
    sys.modules['paho'] = types.ModuleType('paho')
    sys.modules['paho.mqtt'] = types.ModuleType('paho.mqtt')
    sys.modules['paho.mqtt.client'] = types.ModuleType('paho.mqtt.client')
    setattr(sys.modules['paho.mqtt.client'], 'Client', MagicMock(return_value=mqtt_client))
    wrapper = MqttClientWrapper(dispatcher, "localhost")
    parser = lambda _: ControlMsg(board_id=1, fan=10, led=20, temperature=25.0, light_intensity=50.0)
    wrapper.register_topic_handler("topic", parser)
    mqtt_client.is_connected.return_value = True
    wrapper.register_topic_handler("topic2", parser)
    wrapper._on_connect(mqtt_client, None, {}, 0)
    assert "topic" in wrapper._topic_parsers

def test_mqtt_client_wrapper_on_message(monkeypatch):
    dispatcher = MagicMock()
    mqtt_client = MagicMock()
    sys.modules['paho'] = types.ModuleType('paho')
    sys.modules['paho.mqtt'] = types.ModuleType('paho.mqtt')
    sys.modules['paho.mqtt.client'] = types.ModuleType('paho.mqtt.client')
    setattr(sys.modules['paho.mqtt.client'], 'Client', MagicMock(return_value=mqtt_client))
    wrapper = MqttClientWrapper(dispatcher, "localhost")
    called = []
    def parser(payload):
        called.append(payload)
        return ControlMsg(board_id=1, fan=10, led=20, temperature=25.0, light_intensity=50.0)
    wrapper.register_topic_handler("topic", parser)
    msg = MagicMock()
    msg.topic = "topic"
    msg.payload.decode.return_value = '{"boardID": 1, "fan": 10, "led": 20, "temperature": 25.0, "lightIntensity": 50.0, "mode": 0, "messageID": 1, "timestamp": 1.0}'
    wrapper._asyncio_loop = asyncio.get_event_loop()
    wrapper._on_message(mqtt_client, None, msg)
    assert called

@pytest.mark.asyncio
async def test_mqtt_service_context(monkeypatch):
    sys.modules['paho'] = types.ModuleType('paho')
    sys.modules['paho.mqtt'] = types.ModuleType('paho.mqtt')
    sys.modules['paho.mqtt.client'] = types.ModuleType('paho.mqtt.client')
    setattr(sys.modules['paho.mqtt.client'], 'Client', MagicMock())
    monkeypatch.setattr(sys.modules['paho.mqtt.client'], 'Client', MagicMock())
    ctx = MQTTServiceContext("localhost")
    monkeypatch.setattr(ctx.publish_client, "is_connected", lambda: True)
    monkeypatch.setattr(ctx.subscribe_client, "is_connected", lambda: True)
    assert ctx.is_connected()
    await ctx.start()
    await ctx.stop()
    msg = ControlMsg(board_id=1, fan=10, led=20, temperature=25.0, light_intensity=50.0)
    monkeypatch.setattr(ctx.control_cmd_pub, "add_msg", AsyncMock())
    await ctx.publish_control_command(msg)
    with pytest.raises(TypeError):
        await ctx.publish_control_command(StatusMsg(1, Status.OK))