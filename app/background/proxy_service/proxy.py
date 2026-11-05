import socket
import json
from typing import Any
from threading import Event
from background.wrapers.wrapers import Threaded

class Proxy_TCP:
    """
    A TCP socket proxy to route data to internal services.
    """
    class InsufficientArgumentError(Exception): pass
    class MissingCalbackError(Exception): pass

    def __init__(
            self,
            incomming:socket.socket|None= None,
            outgoing_addres:tuple[str, ...]|None= None,
            bind:tuple[str, ...]|None = None,
            listener:bool = False,
            callback:object|None = None
        ) -> None:
        self.client: socket.socket|None = incomming
        self.server_address:tuple[str, ...]|None = outgoing_addres
        self.__alive:bool = True

        self.run_event = Event()

        if listener:
            self.listener(bind, callback) # Starts a background listener for new incomming connections

    @property
    def alive(self):
        return self.__alive

    def stop(self):
        self.__alive = False
    
    @Threaded
    def listener(self, bind:tuple[str, ...]|None, callback):
        if bind is None:
            bind = ("127.0.0.1", 80)
        if callback is None:
            raise self.MissingCalbackError("the listener requires a callback function to be set to perform an action when a connection is recieved")

        main_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        main_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        main_sock.bind(bind)
        main_sock.listen(1)
        print(main_sock)

        while self.alive:
            client, client_address = main_sock.accept()
            print(client_address)
            callback(client, client_address)

    def show_recieved_data(self):
        if self.client is not None:
            return self.client.recv(1024, socket.MSG_PEEK)
        else: return b""

    def return_client(self, data:Any):
        if self.client is None:
            raise self.InsufficientArgumentError("Calling this function requires the 'client' to be set")

        print(f"Returned: {data}")
        if isinstance(data, dict):
            self.client.sendall(json.dumps(data).encode())
        elif isinstance(data, str):
            self.client.sendall(data.encode())
        elif isinstance(data, bytes):
            self.client.sendall(data)
        
        self.stop()

    def halt(self):
        self.run_event.wait()

    def handle_proxy(self):
        if self.server_address is None or self.client is None:
            raise self.InsufficientArgumentError("Calling this function requires the 'client' and 'server_addres' to be set")
        
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.connect(self.server_address)

        def start():
            self.run_event.set()

        @Threaded
        def forward(src:socket.socket, dst:socket.socket, tag:str| None= None):
            self.halt()

            while self.alive:
                try:
                    data = src.recv(4092)
                    if tag:
                        print(f"{tag}: [ {data} ]")
                except:
                    self.stop()
                    break

                if not data:
                    self.stop()
                    if tag:
                        print(f"{tag}: [ Stopped execution ]")
                    break
                try:
                    dst.sendall(data)
                except OSError as error:
                    if error.errno == 9:
                        self.stop()

            if not self.alive:
                src.close()
                dst.close()

        forward(self.client, server_sock)
        forward(server_sock, self.client)

        start()

    def __del__(self):
        pass

if __name__ == "__main__":
    def action(sock:socket.socket, _:tuple[str, ...]):
        prox = Proxy_TCP(sock, ("192.168.1.3", 8000))
        # prox.return_client("HTTP 1.0 200 OK\r\nserver: Proxy\r\ncontent-length: 27\r\ncontent-type: application/json\r\n\r\n" + json.dumps({"object": "Hello, World!"}))
        prox.handle_proxy()
    
    Proxy_TCP(callback= action, listener=True, bind= ("127.0.0.1", 8000))