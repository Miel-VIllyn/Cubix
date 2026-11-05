import json
import os
import base64
import socket
from background.motd.varint import VarInt
from background.static_data_types.dataclasses import *

class MOTD:
    def __init__(self, icon = None) -> None:
        self.icon = icon
    
    @staticmethod
    def get_packet_length(buffer: bytes) -> int | None:
        """
        Reads a VarInt from the start of the buffer and returns the
        expected full packet length (excluding length bytes themselves).
        Returns None if the VarInt is incomplete.
        """
        length = 0
        shift = 0
        for i, byte_val in enumerate(buffer):
            length |= (byte_val & 0x7F) << shift
            if not (byte_val & 0x80):
                return length
            shift += 7
            if shift > 35:
                raise ValueError("VarInt is too big")
        return None
    
    @staticmethod
    def fetch_server_icon(servername:str, worldname:str):
        try:
            with open(os.path.abspath(f"./SERVERS/{servername}/{worldname}/icon.png"), "rb") as file:
                return base64.b64encode(file.read())
        except FileNotFoundError:
            return None

    @staticmethod
    def packet_id(byte:VarInt) -> VarInt:
        return VarInt(byte.value[0:1])

    @staticmethod
    def decode_handshake(byte:VarInt) -> dict[str, VarInt]:
        stdout = {}
        stdout["packet ID"] = VarInt(MOTD.packet_id(byte))
        stdout["Protocol version"] = VarInt(byte.value[1:3])
        stdout["Address length"] = VarInt(byte.value[3:4])
        address_offset = stdout["Address length"].as_int + 3
        stdout["Server IP"] = VarInt(byte.value[4:address_offset + 1])
        stdout["Server port"] = VarInt((byte.value[address_offset + 1: address_offset + 2][0] << 8) | byte.value[address_offset + 2:address_offset + 3][0])
        stdout["Next state"] = VarInt(byte.value[address_offset + 3: address_offset + 4])
        return stdout
    
    def __create_packet(self, packet_id:VarInt, data:VarInt) -> VarInt:
        """
        Combine the packet ID and the data together into a single bytestring
        """
        if data.type == str:
            data = data.encode("utf-8")

        packet = packet_id + data.value
        length = VarInt(len(packet.value))
        return length + packet.value

    def __encode_string(self, string:VarInt) -> bytes:
        encoded = string.encode("utf-8")
        packet = VarInt(len(encoded)) + encoded
        return packet.value

    def create_handshake_packet(self, targetServer:Server_object):
        """
        Create a readymade handshake packet to send after the handshake packet is recieved.
        """
        if self.icon: # If the icon is not set it will not include any keys in the status dictionary
            status = {
                    "version": {"name": "1.21.8", "protocol": targetServer.serverVersion}, # when server is offline copy protocol version from client, so error becomes visible
                    "players": {"max": 0, "online": 0}, # Error codes can be shown in player count ( 0/0 , server is offline ) ( 204/0 , OK server is starting no responce code ) ( 200/"responce code" , OK server is starting with responce code ) ( 400/"Error state" , Starting server has failed with responce code )
                    "description": {"text": f"Server '{targetServer.serverName[0:12]}' Is §4§l§nOffline§r     §d§IVersion:§r §f{targetServer.Versions[0]}§r\n§e§nTry connecting to start the server§r\n§kStop Using packet inspectors dipshit"},
                    "favicon": f"data:image/png;base64,{self.icon}", # Only when icon is available # Still need to fix this so the client can understand the image
                    "enforcesSecureChat": False
                    }
        else:
            status = {
                    "version": {"name": "1.21.8", "protocol": targetServer.serverVersion},
                    "players": {"max": 0, "online": 0},
                    "description": {"text": f"Server '{targetServer.serverName[0:12]}' Is §4§l§nOffline§r     §d§IVersion:§r §f{targetServer.Versions[0]}§r\n§e§nTry connecting to start the server§r\n§kStop Using packet inspectors dipshit"},
                    "enforcesSecureChat": False
                    }
        json_data = json.dumps(status)
        data = self.__encode_string(VarInt(json_data))
        return self.__create_packet(VarInt(0x00), VarInt(data)).value # Packet ID in the case of the handshake is 0x00
    
    # Make function available to the outside
    def create_verification_packet(self, packet_id:VarInt, payload:VarInt) -> None:
        return self.__create_packet(packet_id, payload)
    
    @staticmethod
    def RecieveMotdRequest(sock:socket.socket, targetServer:Server_object) -> int:
        """
        :return int: statuscode <br>
        **0**: everything Ok <br>**1**: Connection Terminated <br>**1000**: Connect Request
        """
        # 1. Read handshake
        packet_lenght = MOTD.get_packet_length(sock.recv(1))
        if not packet_lenght:
            return 1
        
        data = sock.recv(packet_lenght)

        stdout:dict[VarInt] = MOTD().decode_handshake(VarInt(data))
        stdout["Protocol version"].as_int

        if stdout["Next state"].as_int == Connect_type.Connect: # Check the connection type
            return 1000
        
        # 2. Read status request
        packet_lenght = MOTD.get_packet_length(sock.recv(1))
        data = sock.recv(packet_lenght)
        if not data:
            return
        
        
            # 3. Send fake MOTD response
        response = MOTD(targetServer.serverIcon).create_handshake_packet(targetServer)
        try:
            sock.sendall(response)
        except Exception as e:
            print("Send error:", e)