from tortoise import fields
from tortoise.models import Model

class BoardData(Model): 
    """
    Represents the data associated with a board in the system.
    
    Attributes:
        id (int): Unique identifier for the board data.
        board_id (int): Identifier for the board.
        temperature (float): Temperature reading from the board.
        light_intensity (int): Light intensity reading from the board.
        humidity (int): Humidity reading from the board.
        timestamp (datetime): Timestamp of when the data was recorded.
    """
    id = fields.IntField(pk=True)
    timestamp = fields.DatetimeField(auto_now_add=True)
    board_id = fields.IntField()
    temperature = fields.FloatField()
    light_intensity = fields.IntField()
    humidity = fields.IntField()
    class Meta:
        table = "board_data"
        ordering = ["-timestamp"]
        unique_together = (("board_id", "timestamp"),)
    