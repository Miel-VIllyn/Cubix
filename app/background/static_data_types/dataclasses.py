from dataclasses import dataclass
from enum import Enum
import socket
import datetime
from background.motd.varint import VarInt

@dataclass
class State:
    class States(Enum):
        ALIVE = "alive"
        SHUTTING_DOWN = "shutting_down"
        DEAD = "dead"
        CRASHED = "crashed"
    state: States
    last_change:datetime.datetime

    def __repr__(self) -> str:
        return f"State<{id(self)}>(state: {self.state}, last_changed: {self.last_change})"

    def __str__(self) -> str:
        return self.__repr__()

@dataclass
class ServerInfo:
    server_name:str
    server_address:tuple[str, ...]
    status:State

@dataclass
class ClientInfo:
    client_address:tuple[str, ...]
    client_socket:socket.socket
    parent:ServerInfo

class Motd:
    class Handshake(Enum):
        STATUS = 1
        LOGIN = 2
        TRANSFER = 3

    @dataclass
    class MotdHandshake:
        protocol_version:VarInt
        server_ip:VarInt
        server_port:VarInt
        intent:VarInt
        packet_id:VarInt = VarInt(0) # Default value is 0

    @dataclass
    class MotdStatusResponse:
        Response:str # Json response
        packet_id:VarInt = VarInt(0)

    class MotdPong:
        Timestamp:int
    
    @dataclass
    class MotdDisconnect:
        Reason:str # Json response with 'text' component
        packet_id:VarInt = VarInt(0) # Default value is 0
