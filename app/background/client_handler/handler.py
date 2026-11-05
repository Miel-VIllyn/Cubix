from background.proxy_service.proxy import Proxy_TCP
from background.static_data_types.dataclasses import *
from background.wrapers.wrapers import Threaded
import json
import time

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

    def handle_offline(self, proxy:Proxy_TCP):
        # Test on disconnect message
        print(proxy.show_recieved_data())
        json_string = json.dumps({"text": "The server is currently OFFLINE, try again later.","color": "red"})
        json_bytes = json_string.encode("utf-8")

        data = b"\x00" + VarInt(len(json_bytes)).as_VarInt + json_bytes
        length = VarInt(len(data)).as_VarInt
        proxy.return_client(length + data)

    def run(self):
        proxy = Proxy_TCP(self.client_info.client_socket, self.client_info.parent.server_address)
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