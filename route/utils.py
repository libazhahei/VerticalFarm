from typing import Optional

from gateway.service import BLEServiceContext, MQTTServiceContext


class GlobalContext:
    """
    Global context for the application.
    This class can be used to store global state or configuration.
    """

    # Singleton instance
    mqtt_service_context: MQTTServiceContext | None
    ble_service_context: BLEServiceContext | None

    global_context: Optional["GlobalContext"] = None

    @classmethod
    def get_instance(cls, mqtt_service_context: MQTTServiceContext | None = None, ble_service_context: BLEServiceContext | None = None) -> "GlobalContext":
        """Get the singleton instance of GlobalContext."""
        if cls.global_context is not None:  
            return cls.global_context
        cls.global_context = cls()
        cls.global_context.mqtt_service_context = mqtt_service_context
        cls.global_context.ble_service_context = ble_service_context
        return cls.global_context
