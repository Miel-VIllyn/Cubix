from dataclasses import dataclass
from enum import Enum
import socket
import datetime
from background.mc_protocol.varint import VarInt
from uuid import UUID
import json

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

# MOTD info
@dataclass
class Profile:
    player_uuid:UUID
    username:str
    property_count:int

class MotdObjects: 
    def byte_package(self) -> bytes: pass

class Motd:
    class Handshake(Enum):
        STATUS = 1
        LOGIN = 2
        TRANSFER = 3

    @dataclass
    class MotdHandshake(MotdObjects):
        protocol_version:VarInt
        server_ip:str
        server_port:int
        intent:VarInt
        packet_id:VarInt = VarInt(0) # Default value is 0

    class Status:
        # Server -> Client
        @dataclass
        class StatusResponse(MotdObjects):
            response:MotdObjects # Json response
            packet_id:VarInt = VarInt(0) # Default value is 0

            def byte_package(self) -> bytes:
                return self.response.byte_package()

        @dataclass
        class PongResonse(MotdObjects):
            timestamp:int # use `int.to_bytes(7609854, byteorder="big", signed=True)` to transform to bytes
            packet_id:VarInt = VarInt(1) # Default value is 1

            def byte_package(self) -> bytes:
                byte_time = self.timestamp.to_bytes(length=8, byteorder="big", signed=True)
                return VarInt(len(self.packet_id.as_VarInt) + len(byte_time)).as_VarInt + self.packet_id.as_VarInt + byte_time


        # Client -> Server
        @dataclass
        class StatusRequest(MotdObjects):
            packet_id:VarInt = VarInt(0) # Default value is 0

        @dataclass
        class PingRequest(MotdObjects):
            timestamp:int # use `int.from_bytes(data, byteorder="big", signed=True)` to transfrom it
            packet_id:VarInt = VarInt(1) # Default value is 1

        @dataclass
        class Status(MotdObjects):
            version:tuple[str, int]
            description:str
            favicon:bytes|None = None
            enforcesecurechat:bool = False

            def byte_package(self) -> bytes:
                message = str(self).encode()
                len_message = VarInt(len(message)).as_VarInt
                return VarInt(1+len(len_message)+len(message)).as_VarInt + b"\x00" + len_message + message

            def __repr__(self) -> str:
                if self.favicon:
                    return json.dumps(
                        {
                            "version": {
                                "name": self.version[0],
                                "protocol": self.version[1]
                            },
                            "description": self.description,
                            "favicon": f"data:image/png;base64,{self.favicon}",
                            "enforceSecureChat": self.enforcesecurechat
                        }
                    )
                else:
                    return json.dumps(
                        {
                            "version": {
                                "name": self.version[0],
                                "protocol": self.version[1]
                            },
                            "description": self.description,
                            "enforceSecureChat": self.enforcesecurechat
                        }
                    )
                
            def __str__(self) -> str:
                return self.__repr__()

    class Login:
        # Server -> Client
        @dataclass
        class Disconnect:
            reason:str # Json response with 'text' component
            color:str
            packet_id:VarInt = VarInt(0) # Default value is 0

            def byte_package(self) -> bytes:
                message = str(self).encode()
                len_message = VarInt(len(message)).as_VarInt
                return VarInt(1+len(len_message)+len(message)).as_VarInt + b"\x00" + len_message + message

            def __repr__(self) -> str:
                return json.dumps(
                    {
                        "text": self.reason,
                        "color": self.color
                    }
                )
        
            def __str__(self) -> str:
                return self.__repr__()

        @dataclass
        class EncryptionRequest:
            server_id:str # Max of 20 characters long. Always empty when sent by the vanilla server.
            public_key:bytes # The server's public key, in bytes.
            verify_token:bytes # A sequence of random bytes generated by the server.
            should_authenticate:bool # Whether the client should attempt to authenticate through mojang servers, when server is in online mode this is true
            packet_id:VarInt = VarInt(1) # Default value is 1


        # Not realy usefull, after the encryption request, trafic becomes unreadable to the proxy
        @dataclass
        class LoginSucces:
            """
            First message after login request (if online-mode=false)
            First message after encryption (if online-mode=true), is unreadable though
            Server->Client:: [
                b'\x03\x03\x80\x02' # Set compression
                b'1\x00\x02'
                b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                b'\x0d'
                b'username'
                b'\x00'
                b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            ]
            """
            profile:Profile
            session_id:UUID # 16 bytes long. Encoded as an unsigned 128-bit integer (or two unsigned 64-bit integers: the most significant 64 bits and then the least significant 64 bits)
            packet_id:VarInt = VarInt(2) # Default value is 2

        @dataclass
        class SetCompression:
            threshold:VarInt
            packet_id:VarInt = VarInt(3)
        
        # Client -> Server
        @dataclass
        class LoginStart(MotdObjects):
            """
            First message after Handshake
            """
            username:str # Player's Username.
            player_uuid:UUID # The UUID of the player logging in. Unused by the vanilla server.
            packet_id:VarInt = VarInt(0)

            def byte_package(self) -> bytes:
                message = self.packet_id.as_VarInt + VarInt(len(self.username)).as_VarInt + self.username.encode() + self.player_uuid.bytes
                return VarInt(len(message)).as_VarInt + message

        @dataclass
        class LoginAck:
            packet_id:VarInt = VarInt(3)

class Packet_Type(Enum):
    Handshake = 0
    STATUS = 0
    LOGIN = 0
    PONG = 1
