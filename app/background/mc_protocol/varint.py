import struct
import time

class VarInt:
    DEBUG = False
    def __init__(self, input: int|bytes|str):
        self.input = input

    def __decode(self, data:bytes) -> int | bytes:
        if self.DEBUG:
            start = time.perf_counter_ns()

        ind = 0
        shift = 0
        result = 0
        while True:
            if ind >= len(data):
                break
            byte_val = data[ind]
            result |= (byte_val & 0x7F) << shift
            if not (byte_val & 0x80):
                break
            shift += 7
            if shift > 35:
                raise ValueError("VarInt is too big")
            ind += 1

        if self.DEBUG:
            stop = time.perf_counter_ns()
            print(f"__decode(): {stop - start}ns")
        self.input = data[:ind+1:]
        return result
    
    def __encode(self, value:str|bytes|int|str) -> bytes:
        if self.DEBUG:
            start = time.perf_counter_ns()
        
        out = b""
        while True:
            temp = value & 0x7F
            value >>= 7
            if value != 0:
                temp |= 0x80
            out += struct.pack("B", temp)
            if value == 0:
                break
        
        if self.DEBUG:
            stop = time.perf_counter_ns()
            print(f"__encode(): {stop - start}ns")
        return out

    def encode(self, encoding:str = None) -> bytes:
        self.input = self.input.encode(encoding)
        return self.input

    def decode(self, encoding:str = None) -> str:
        self.input = self.input.decode(encoding)
        return self.input

    @property
    def value(self) -> int|bytes:
        return self.input
    
    @property
    def type(self) -> type:
        return type(self.input)

    @property
    def as_int(self) -> int:
        if isinstance(self.input, bytes):
            return self.__decode(self.input)
        elif isinstance(self.input, int):
            return int(self.input)
        else:
            return -1
    
    @property
    def as_VarInt(self) -> bytes:
        if isinstance(self.input, int):
            return self.__encode(self.input)
        elif isinstance(self.input, bytes):
            return self.input
        else:
            return b""

    # Add multiple items together and convert them to a VarInt type
    def __add__(self, addition:str|bytes|int):
        if type(addition) == int:
            addition = self.__encode(addition)

        if type(self.input) == int:
            self.input = self.__encode(self.input)
            if type(addition) == str:
                addition = addition.encode()
        
        elif type(self.input) == bytes:
            if type(addition) == str:
                addition = addition.encode()
            elif type(addition) == VarInt:
                addition = addition.as_VarInt
        
        elif type(self.input) == str:
            try:
                if type(addition) == bytes:
                    addition = addition.decode()
            except UnicodeDecodeError:
                self.input = self.input.encode()
        self.input += addition
        return self
    
    def __str__(self) -> str:
        return str(self.value)