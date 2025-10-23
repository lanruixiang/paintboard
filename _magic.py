import json
import requests
import uuid

# -------------------- 常量定义 -------------------------------------------

BASE_URL = "paintboard.luogu.me"
GET_TOKEN_URL = f"https://{BASE_URL}/api/auth/gettoken"
GET_BOARD_URL = f"https://{BASE_URL}/api/paintboard/getboard"
WS_URL = f"wss://{BASE_URL}/api/paintboard/ws"

PING = 0xfc
PAINT_MESSAGE = 0xfa
PAINT_RESULT = 0xff

PONG = 0xfb
PAINT = 0xfe

SUCCESS = 0xEF                # 成功
COOLING_DOWN = 0xEE           # 正在冷却
INVALID_TOKEN = 0xED          # Token 无效
BAD_REQUEST = 0xEC            # 请求格式错误
NO_PERMISSION = 0xEB          # 无权限
SERVER_ERROR = 0xEA           # 服务器错误

MAX_PACKETS_PER_SECOND = 256
SEND_INTERVAL = 1 / MAX_PACKETS_PER_SECOND  # 1.1 秒最多发送 256 个包，防止波动导致连接断开
MAX_PACKET_SIZE = 32 * 1024                   # 单位字节

# ------------------------ 自定义队列/双端队列 ------------------------------

class QueueError(Exception):
    pass

class Queue:
    def __init__(self, maxlen=10000):
        self.arr = [None for _ in range(maxlen)]
        self.head = 0
        self.tail = 0
        self.maxlen = maxlen
    def push(self, item):
        if self.size() == self.maxlen - 1:
            raise QueueError("队列已满")
        self.arr[self.tail] = item
        self.tail += 1
        if self.tail == self.maxlen:
            self.tail = 0
    def front(self):
        if self.empty():
            raise QueueError("队列为空")
        return self.arr[self.head]
    def pop(self):
        if self.empty():
            raise QueueError("队列为空")
        self.arr[self.head] = None
        self.head += 1
        if self.head == self.maxlen:
            self.head = 0
    def empty(self) -> bool:
        return self.head == self.tail
    def size(self) -> int:
        res = self.tail - self.head
        if res < 0:
            res += self.maxlen
        return res

class Deque:
    def __init__(self, maxlen=10000):
        self.arr = [None for _ in range(maxlen)]
        self.head = 0
        self.tail = maxlen - 1
        self.maxlen = maxlen
    def push_back(self, item):
        if self.size() == self.maxlen - 1:
            raise QueueError("队列已满")
        self.tail += 1
        if self.tail == self.maxlen:
            self.tail = 0
        self.arr[self.tail] = item
    def push_front(self, item):
        if self.size() == self.maxlen - 1:
            raise QueueError("队列已满")
        self.head -= 1
        if self.head == -1:
            self.head = self.maxlen - 1
        self.arr[self.head] = item
    def front(self):
        if self.empty():
            raise QueueError("队列为空")
        return self.arr[self.head]
    def back(self):
        if self.empty():
            raise QueueError("队列为空")
        return self.arr[self.tail]
    def pop_back(self):
        if self.empty():
            raise QueueError("队列为空")
        self.arr[self.tail] = None
        self.tail -= 1
        if self.tail == -1:
            self.tail = self.maxlen - 1
    def pop_front(self):
        if self.empty():
            raise QueueError("队列为空")
        self.arr[self.head] = None
        self.head += 1
        if self.head == self.maxlen:
            self.head = 0
    def empty(self) -> bool:
        return self.head == self.tail + 1 or self.head == 0 and self.tail == self.maxlen - 1    
    def size(self) -> int:
        res = self.tail - self.head + 1
        if res < 0:
            res += self.maxlen
        return res    

# ----------------------- 工具函数 --------------------------------

""" 通过 uid 与 AccessKey 获取 Token """
def get_token(uid:int, access_key:str) -> str:
    try:
        res = requests.post(
            GET_TOKEN_URL,
            json={
                "uid": uid,
                "access_key": access_key
            }
        )
        data = json.loads(res.text)
        return data["data"]["token"]
    except Exception as e:
        print(e)

""" 将数字转换为 k 字节小端序字节流 """
def to_bytes(val:int, k:int=1) -> bytes:
    return val.to_bytes(k, "little")

""" 将 token 转换为小端序字节流 """
def uuid_to_bytes(token:str) -> bytes:
    return uuid.UUID(token).bytes

""" 将 uid 转换为 3 * uint8 字节流"""
def uid_to_bytes(uid:int) -> bytes:
    a = to_bytes(uid & 0b11111111, 1)
    b = to_bytes((uid >> 8) & 0b11111111, 1)
    c = to_bytes((uid >> 16) & 0b11111111, 1)
    return a + b + c

""" 将小端字节流转换为 int """
def to_int(b:bytes):
    if isinstance(b, int):
        return b
    return int.from_bytes(b, "little")
    
