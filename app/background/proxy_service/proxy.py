import socket
import json
from typing import Any

# -------------------------------------------------------------------
# Put this in it's own file
from threading import Thread, Lock, Event

# Thread wrapper
def Threaded(func):
    def wrapper(*args:list[Any], **kwargs: dict[str, Any]) -> Thread:
        thread = Thread(target=func, args=args, kwargs=kwargs)
        thread.start()
        return thread
    return wrapper
# -------------------------------------------------------------------

class Proxy_TCP:
    """
    A TCP socket proxy to route data to internal services.
    """
    class InsufficientArgumentError(Exception): pass
    class MissingCalbackError(Exception): pass

    def __init__(
            self,
            incomming:socket.socket|None= None,
            outgoing_addres:socket._Address|None= None,
            bind:socket._Address|None = None,
            listener:bool = False,
            callback:object|None = None
        ) -> None:
        self.mutex = Lock()
        self.client: socket.socket|None = incomming
        self.server_address:socket._Address|None = outgoing_addres
        self.__alive:bool = True

        self.run_event = Event()

        if listener:
            self.listener(bind, callback) # Starts a background listener for new incomming connections
            print("Listener is now running")

    @property
    def alive(self):
        return self.__alive

    def stop(self):
        self.__alive = False
    
    @Threaded
    def listener(self, bind:socket._Address, callback):
        if bind is None:
            bind = ("127.0.0.1", 80)
        if callback is None:
            raise self.MissingCalbackError("the listener requires a callback function to be set to perform an action when a connection is recieved")

        main_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        main_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        main_sock.bind(bind)
        main_sock.listen(1)

        while self.alive:
            client, client_address = main_sock.accept()
            callback(client, client_address)
        

    def return_client(self, data:Any):
        if self.client is None:
            raise self.InsufficientArgumentError("Calling this function requires the 'client' to be set")
        with self.mutex:
            print(f"Returned: {data}")
            if type(data) is dict:
                self.client.sendall(json.dumps(data).encode())
            elif type(data) is str:
                self.client.sendall(data.encode())
        
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
                dst.sendall(data)
            if not self.alive:
                src.close()
                dst.close()

        forward(self.client, server_sock, tag="Client -> Server")
        forward(server_sock, self.client, tag="Server -> Client")

        start()


def action(sock:socket.socket, _:socket._Address):
    prox = Proxy_TCP(sock, ("192.168.1.3", 8000))
    # prox.return_client("HTTP 1.0 200 OK\r\nserver: Proxy\r\ncontent-length: 27\r\ncontent-type: application/json\r\n\r\n" + json.dumps({"object": "Hello, World!"}))
    prox.handle_proxy()

if __name__ == "__main__":
    Proxy_TCP(callback= action, listener=True, bind= ("127.0.0.1", 8000))