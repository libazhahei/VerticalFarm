
import asyncio
import sys
import types
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
from datetime import datetime, timedelta

import gateway.service as service_mod
from gateway.service import BLEClientWrapper, BLEServiceContext
from gateway.msg import SensorDataMsg, MQTTMessageType
from gateway.subscriber import MessageDispatcher, SensorDataSubscriber
from data.tables import BoardData, BoardDataBatchWriter


@pytest.mark.asyncio
async def test_ble_client_wrapper_register_and_connect(monkeypatch):
    dispatcher = MessageDispatcher()
    device_id = 1
    fake_device = MagicMock()
    fake_device.name = f"CropWaifu-Board-{device_id:01x}"
    fake_device.address = "00:11:22:33:44:55"
    monkeypatch.setattr(service_mod, "BleakScanner", MagicMock())
    service_mod.BleakScanner.discover = AsyncMock(return_value=[fake_device])
    fake_ble_client = MagicMock()
    fake_ble_client.is_connected = False
    fake_ble_client.connect = AsyncMock()
    fake_ble_client.start_notify = AsyncMock()
    fake_ble_client.disconnect = AsyncMock()
    monkeypatch.setattr(service_mod, "BleakClient", MagicMock(return_value=fake_ble_client))

    wrapper = BLEClientWrapper([device_id], dispatcher)
    handler = MagicMock()
    wrapper.register_notification_handler(device_id, handler)
    monkeypatch.setattr(service_mod, "get_characteristic_uuid", lambda x: "uuid-1")
    monkeypatch.setattr(asyncio, "create_task", lambda coro: asyncio.ensure_future(coro))
    await wrapper.start()
    assert wrapper.is_running
    assert device_id in wrapper.ble_devices
    assert device_id in wrapper.connection_tasks

    await wrapper.stop()
    assert not wrapper.is_running
    assert wrapper.ble_clients == {}


@pytest.mark.asyncio
async def test_ble_client_wrapper_on_ble_notification_dispatch(monkeypatch):
    dispatcher = MessageDispatcher()
    wrapper = BLEClientWrapper([1], dispatcher)
    handler = MagicMock(return_value=SensorDataMsg(1, 25.0, 100, 1, 50.0))
    wrapper.register_notification_handler(1, handler)
    dispatcher.put_message = AsyncMock()

    char = MagicMock()
    char.uuid = "1"
    wrapper._characteristic_parsers = {"1": handler}

    data = bytearray([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    await wrapper.on_ble_notification(char, data)
    handler.assert_called_once_with(data)
    dispatcher.put_message.assert_awaited()



@pytest.mark.asyncio
async def test_ble_service_context_start_stop(monkeypatch):
    with patch.object(service_mod, "BLEClientWrapper") as MockBLEClientWrapper, \
         patch.object(service_mod, "BoardDataBatchWriter") as MockBatchWriter, \
         patch.object(service_mod, "MessageDispatcher") as MockMessageDispatcher, \
         patch.object(service_mod, "SensorDataSubscriber") as MockSensorDataSubscriber:
        fake_batch_writer = MockBatchWriter.return_value
        fake_batch_writer.start = AsyncMock()
        fake_batch_writer.stop = AsyncMock()
        fake_batch_writer.fetch = AsyncMock(return_value=[])
        fake_batch_writer.fetch_since = AsyncMock(return_value=[])
        monkeypatch.setattr(service_mod.BoardDataBatchWriter, "get_instance", lambda: fake_batch_writer)
        fake_msg_dispatcher = MockMessageDispatcher.return_value
        fake_msg_dispatcher.start = AsyncMock()
        fake_msg_dispatcher.stop = AsyncMock()
        fake_ble_client = MockBLEClientWrapper.return_value
        fake_ble_client.start = AsyncMock()
        fake_ble_client.stop = AsyncMock()

        ctx = BLEServiceContext([1, 2])
        await ctx.start()
        assert ctx.is_running
        await ctx.stop()
        assert not ctx.is_running



def test_ble_service_context_connected_devices():
    with patch.object(service_mod, "BLEClientWrapper") as MockBLEClientWrapper:
        ctx = BLEServiceContext([1, 2, 3])
        ctx.ble_client.ble_devices = {1: MagicMock(), 2: MagicMock()}
        assert set(ctx.connected_devices()) == {1, 2}



@pytest.mark.asyncio
async def test_ble_service_context_fetch_data(monkeypatch):
    with patch.object(service_mod, "BoardData") as MockBoardData, \
         patch.object(service_mod, "BoardDataBatchWriter") as MockBatchWriter:
        fake_query = MagicMock()
        fake_query.filter.return_value = fake_query
        fake_query.order_by.return_value.all = AsyncMock(return_value=[BoardData(board_id=1, temperature=25.0, light_intensity=100, humidity=50)])
        MockBoardData.filter.return_value = fake_query
        fake_batch_writer = MockBatchWriter.return_value
        # fake_batch_writer.fetch_since = AsyncMock(return_value=[BoardData(board_id=1, temperature=25.0, light_intensity=100, humidity=50)])
        monkeypatch.setattr(service_mod.BoardDataBatchWriter, "get_instance", lambda: fake_batch_writer)

        ctx = BLEServiceContext([1])
        buffer_data = BoardData(board_id=1, temperature=26.0, light_intensity=101, humidity=51)
        buffer_data.timestamp = datetime.now()
        ctx.batch_writer.fetch_since = AsyncMock(return_value=[buffer_data] + [BoardData(board_id=1, temperature=25.0, light_intensity=100, humidity=50)])
        

        since = datetime.now() - timedelta(days=1)
        data = await ctx.fetch_data(since, [1])
        assert any(d.temperature == 25.0 for d in data)
        assert any(d.temperature == 26.0 for d in data)

@pytest.mark.asyncio
async def test_ble_service_context_fetch_data_from_database(monkeypatch):
    with patch.object(service_mod, "BoardData") as MockBoardData, \
            patch.object(service_mod, "BoardDataBatchWriter") as MockBatchWriter:
        fake_query = MagicMock()
        fake_query.filter.return_value = fake_query
        fake_query.order_by.return_value.all = AsyncMock(return_value=[
            BoardData(board_id=1, temperature=25.0, light_intensity=100, humidity=50, timestamp=datetime.now() - timedelta(hours=1)),
            BoardData(board_id=2, temperature=22.0, light_intensity=90, humidity=45, timestamp=datetime.now() - timedelta(hours=2))
        ])
        MockBoardData.filter.return_value = fake_query

        fake_batch_writer = MockBatchWriter.return_value
        fake_batch_writer.fetch = AsyncMock(return_value=[])
        fake_batch_writer.fetch_since = AsyncMock(return_value=[
            BoardData(board_id=1, temperature=25.0, light_intensity=100, humidity=50, timestamp=datetime.now() - timedelta(hours=1)),
            BoardData(board_id=2, temperature=22.0, light_intensity=90, humidity=45, timestamp=datetime.now() - timedelta(hours=2))
        ])
        monkeypatch.setattr(service_mod.BoardDataBatchWriter, "get_instance", lambda: fake_batch_writer)

        ctx = BLEServiceContext([1, 2])
        since = datetime.now() - timedelta(days=1)
        data = await ctx.fetch_data(since, [1, 2])

        assert len(data) == 2
        assert any(d.temperature == 25.0 for d in data)
        assert any(d.temperature == 22.0 for d in data)


