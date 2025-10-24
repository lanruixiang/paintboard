import websocket
import time
from concurrent.futures import ThreadPoolExecutor

class Queue:
    def __init__(self, maxsize=10000):
        self.arr = [None for _ in range(maxsize)]
        self.head = 0
        self.tail = 0
        self.maxsize = maxsize
    def push(self, item):
        self.arr[self.tail] = item
        self.tail += 1
        if self.tail == self.maxsize:
            self.tail = 0
    def front(self):
        return self.arr[self.head]
    def pop(self):
        res = self.arr[self.head]
        self.head += 1
        if self.head == self.maxsize:
            self.head = 0
        return res
    def empty(self):
        return self.tail == self.head
    def size(self):
        res = self.tail - self.head
        if res < 0:
            res += self.maxsize
        return res

BASE_URL = "paintboard.luogu.me"
WS_URL = f"wss://{BASE_URL}/api/paintboard/ws?readonly=1"

executor = ThreadPoolExecutor(max_workers=10)

PING = 0xfc
PAINT_MESSAGE = 0xfa
PAINT_RESULT = 0xff

buffer = bytearray()
paint_list = Queue()

def on_message(ws, message):
    global buffer, paint_list
    buffer.extend(message)
    while len(buffer) > 0:
        if buffer[0] == PING:
            del buffer[0]
            ws.send((0xfb).to_bytes(1, 'little'), websocket.ABNF.OPCODE_BINARY)
        elif buffer[0] == PAINT_MESSAGE:
            paint_list.push(time.time())
            if len(buffer) < 8:
                break
            del buffer[0 : 8]
        elif buffer[0] == PAINT_RESULT:
            if len(buffer) < 6:
                break
            del buffer[0 : 6]
        else:
            print(f"[ERROR] code:{buffer[0]}")

def on_open_forever():
    while True:
        while not paint_list.empty():
            if time.time() - paint_list.front() >= 10:
                paint_list.pop()
            else:
                break
        # if paint_list.size() / 10 > 100:
        #     print("[WARN] ", end="")
        print(f"全局绘画消息：{paint_list.size() / 2.5} 条 / 4s")
        time.sleep(1)

def on_open(ws):
    print("连接成功")
    executor.submit(on_open_forever)

app = websocket.WebSocketApp(
    WS_URL,
    on_message=on_message,
    on_open=on_open
)

app.run_forever()