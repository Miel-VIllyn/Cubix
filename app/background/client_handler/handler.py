from background.proxy_service.proxy import Proxy_TCP
from background.static_data_types.dataclasses import *
from background.mc_protocol.motd import MC_protocol
from background.mc_protocol.varint import VarInt
import json

class Client:
    class UnhandelableStateError(Exception): pass

    def __init__(self, client_info:ClientInfo):
        self.client_info = client_info

        self._alive:bool = True
        self.kill_everything:bool = False
        self.parrent_crashed:bool = False

    @property
    def alive(self):
        match self.client_info.parent.status.state:
            case State.States.ALIVE:
                self._alive = True
                return self._alive
            case State.States.SHUTTING_DOWN:
                # Gracefully shutdown everything
                self._alive = False
                return self._alive
            case State.States.DEAD:
                # If parrent class is shut down, but thread is still alive,
                # forcefully prevent any other tasks from running to prevent
                # security issues
                self._alive = False
                self.kill_everything = True
                return self._alive
            case State.States.CRASHED:
                # Prevent any other tasks from starting and wait for parent
                # to be restarted
                self._alive = False
                self.parrent_crashed = True
                return self._alive
            case _:
                raise self.UnhandelableStateError(f"{self.client_info.parent.status} isn't a valid state to be in.\nCheck for errors in the serverhandler for the server '{self.client_info.parent.server_name}'")

    def parent_alive(self) -> bool:
        if self.client_info.parent.status.state == State.States.ALIVE:
            return True
        else:
            return False

    def return_ping(self, proxy:Proxy_TCP, obj:MotdObjects, protocol_version:int|None = None):
        if isinstance(obj, Motd.Status.StatusRequest):
            message = Motd.Status.Status(
                    ("Dead", protocol_version),
                    "This server is dead",
                    enforcesecurechat= True
                ).byte_package()

            proxy.return_client(message)
        elif isinstance(obj, Motd.Status.PingRequest):
            message = Motd.Status.PongResonse(
                obj.timestamp
            ).byte_package()

            proxy.return_client(message)

    def return_disconnect(self, proxy:Proxy_TCP):
        message = Motd.Login.Disconnect(
            "The server is offline, try again later",
            "red"
        ).byte_package()
        proxy.return_client(message)

    def handle_offline(self, proxy:Proxy_TCP):
        login = False
        connect_type = 0
        protocol_version = 0

        while proxy.alive:
            data = proxy.show_recieved_data(4092)
            split_data = MC_protocol.seperate_concatenated_packets(data)

            built_objects:list[MotdObjects] = []

            for _, packet in split_data:
                built_object = MC_protocol.build_packet_classes(packet, login)
                built_objects.append(built_object)
                if isinstance(built_object, Motd.MotdHandshake):
                    connect_type = built_object.intent.as_int
                    protocol_version = built_object.protocol_version.as_int
                    if built_object.intent.as_int == Motd.Handshake.LOGIN.value:
                        login = True
                    elif built_object.intent.as_int == Motd.Handshake.TRANSFER.value:
                        login = True

            for obj in built_objects:
                if connect_type == Motd.Handshake.LOGIN.value or connect_type == Motd.Handshake.TRANSFER.value:
                    self.return_disconnect(proxy)
                elif connect_type == Motd.Handshake.STATUS.value:
                    self.return_ping(proxy, obj, protocol_version)

    def run(self):
        proxy = Proxy_TCP(self.client_info.client_socket, self.client_info.parent.server_address)
        # Grab handshake packet
        if self.alive and self.parent_alive():
            proxy.handle_proxy()
        elif not self.alive and self.parent_alive():
            proxy.return_client(b"0x00" + json.dumps({"text": "The server had an unexpected error and you have been disconnected.","color": "red"}).encode())
        else:
            self.handle_offline(proxy)


# testserver is hosted on the local PC
# minecraft client sends trafic to the server this is hosted on
# and that server redirects the trafic to the testserver
# technicaly works over a VPN or over the public internet (Not recomended though)
# best situation host minecraft on server this is being hosted on, and redirect to localhost

import socket

def callback(sock:socket.socket, address:tuple[str, ...]):
    print(address)
    info = ClientInfo(
        address,
        sock,
        ServerInfo(
            "Test",
            ("192.168.1.223", 25565),
            State(
                State.States.ALIVE,
                datetime.datetime.now()
            )
        )
    )
    client = Client(info)
    client.run()

Proxy_TCP(bind= ("", 25555), listener= True, callback=callback)