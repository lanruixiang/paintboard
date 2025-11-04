import time
import random
import requests
import websocket
import json
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
from _magic import *
# -----------------------------------------------------------

IMAGE_LIST = [
    ("m7.png", 550, 0, 150, 150),
]

CD = 50

# ------------------- 创建线程池    -------------------------

executor = ThreadPoolExecutor(max_workers=10)

# ------------------- 创建 token 池 -------------------------

class TokenPool:
    def __init__(self):
        self.token_list = Queue()
        self.token_count = 0
    def add_token(self, uid:int, token:str):
        self.token_list.push((uid, token))
        self.token_count += 1
    def get_token(self) -> tuple[int, str]:
        res = self.token_list.front()
        self.token_list.pop()
        self.token_list.push(res)
        return res
    def count(self) -> int:
        return self.token_count

token_pool = TokenPool()

# ------------------------ 获取版面 ----------------------------

class Board:
    def __init__(self):
        self.r = [[None for _ in range(600)] for _ in range(1000)]
        self.g = [[None for _ in range(600)] for _ in range(1000)]
        self.b = [[None for _ in range(600)] for _ in range(1000)]
    def set_rgb(self, x:int, y:int, r:int, g:int, b:int):
        self.r[x][y] = r
        self.g[x][y] = g
        self.b[x][y] = b
    def get_rgb(self, x:int, y:int) -> tuple[int, int, int]:
        return (
            self.r[x][y],
            self.g[x][y],
            self.b[x][y]
        )

def get_board() -> Board:
    resp = requests.get(GET_BOARD_URL)

    data = resp.content

    res = Board()

    for y in range(0, 600):
        for x in range(0, 1000):
            res.set_rgb(
                x, y,
                data[y * 1000 * 3 + x * 3],
                data[y * 1000 * 3 + x * 3 + 1],
                data[y * 1000 * 3 + x * 3 + 2]
            )
    return res

# ------------------------ 定义绘画任务 ------------------------

class PaintWork:
    def __init__(self, x:int, y:int, r:int, g:int, b:int):
        self.x = x
        self.y = y
        self.r = r
        self.g = g
        self.b = b

# ------------------------ 创建任务队列 ------------------------

class WorkList:
    def __init__(self):
        self.work_list = Deque(500000)
    def add_work(self, work:PaintWork, is_front:bool=False):
        if(is_front):
            self.work_list.push_front(work)
        else:
            self.work_list.push_back(work)
    def get_work(self) -> PaintWork | None:
        if(self.work_list.empty()):
            return None
        res = self.work_list.front()
        self.work_list.pop_front()
        return res

work_list = WorkList()

# ---------------------- 读取图片 ----------------------------

class MagicImage:
    def __init__(self, x:int, y:int):
        self.r = [[None for _ in range(y)] for _ in range(x)]
        self.g = [[None for _ in range(y)] for _ in range(x)]
        self.b = [[None for _ in range(y)] for _ in range(x)]
        self.len_x = x
        self.len_y = y
    def setpixel(self, x:int, y:int, r:int, g:int, b:int):
        self.r[x][y] = r
        self.g[x][y] = g
        self.b[x][y] = b
    def getpixel(self, x:int, y:int) -> tuple[int, int, int]:
        return (self.r[x][y], self.g[x][y], self.b[x][y])
    def insert_image(self, image:"MagicImage", start_x:int, start_y:int):
        for x in range(image.len_x):
            for y in range(image.len_y):
                r, g, b = image.getpixel(x, y)
                self.setpixel(x + start_x, y + start_y, r, g, b)

def read_image(path:str, x:int, y:int) -> MagicImage:
    if(path != "RANDOM"):
        img = Image.open(path).convert("RGB")
        img = img.resize((x, y), resample=Image.LANCZOS)
        
    res = MagicImage(x, y)
    for i in range(0, x):
        for j in range(0, y):
            if(path != "RANDOM"):
                r, g, b = img.getpixel((i, j))
            else:
                r = random.randint(0, 255)
                g = random.randint(0, 255)
                b = random.randint(0, 255)
            res.setpixel(i, j, r, g, b)
                
    return res

# ---------------------- 创建整个板面的绘画图片 -----------------------

all_board = MagicImage(1000, 600)

# ---------------------- 从总版面创建维护表 -----------------------

class DefendMap:
    def __init__(self):
        self.board = None
        self.i_right = None
    def set_img(self, board:MagicImage):
        self.board = board
        self.i_right = [[True for _ in range(600)] for _ in range(1000)]
    def getpixel(self, x:int, y:int) -> tuple[int, int, int]:
        if(not self.is_defended(x, y)):
            return (-1, -1, -1)
        return self.board.getpixel(x, y)
    def is_defended(self, x:int, y:int) -> bool:
        r, g, b = self.board.getpixel(x, y)
        if((r, g, b) == (None, None, None)):
            return False
        return True
    def is_right(self, x:int, y:int) -> bool:
        if(not self.is_defended(x, y)):
            return True
        return self.i_right[x][y]
    def right(self, x:int, y:int, op:bool):
        if(not self.is_defended(x, y)):
            return
        self.i_right[x][y] = op

defend_map = DefendMap()
        
# --------------------- 将图片加入任务列表 ----------------------------

def add_image():
    global work_list, defend_map, all_board

    time.sleep(2)

    # 获取版面

    board = get_board()
    cnt = 0

    for j in range(600):
        for i in range(1000):
            if(not defend_map.is_defended(i, j)):
                continue
            r, g, b = all_board.getpixel(i, j)
            br, bg, bb = board.get_rgb(i, j)
            if((br, bg, bb) == (r, g, b)):
                continue
            work_list.add_work(
                PaintWork(i, j, r, g, b)
            )
            cnt += 1

# ---------------------- 记录已发送列表 ----------------------

sended = [None]
count = 0

# ---------------------- 创建 WebSocketApp -------------------

# 时间

def gettime() -> str:
    tm = time.time()
    local_time = time.localtime(tm)
    res = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
    return res

buffer = bytearray()
sender_buffer = bytearray()

# 绘画操作加入 sender_buffer
def draw_a_point(pt:PaintWork):
    global sender_buffer, token_pool, count, sended
    uid, token = token_pool.get_token()
    count += 1
    sended.append(pt)
    my_id = count
    data = (
        to_bytes(PAINT, 1)
        + to_bytes(pt.x, 2)
        + to_bytes(pt.y, 2)
        + to_bytes(pt.r, 1)
        + to_bytes(pt.g, 1)
        + to_bytes(pt.b, 1)
        + uid_to_bytes(uid)
        + uuid_to_bytes(token)
        + to_bytes(my_id, 4)
    )
    sender_buffer.extend(data)

# 处理绘画消息
def handle_paint_message(x:int, y:int, new_r:int, new_g:int, new_b:int):
    global defend_map, work_list
    if(not defend_map.is_defended(x, y)):
        return 
    r, g, b = defend_map.getpixel(x, y)
    if(new_r == r and new_g == g and new_b == b):
        defend_map.right(x, y, True)
    else:
        if(defend_map.is_right(x, y)):
            work_list.add_work(PaintWork(x, y, r, g, b), False)
        defend_map.right(x, y, False)

# 接收消息
def on_message(ws, message):
    global buffer, sender_buffer, work_list, sended
    buffer.extend(message)
    while(len(buffer) > 0):
        if(buffer[0] == PING):
            sender_buffer.extend(to_bytes(PONG, 1))
            del buffer[0]
        elif(buffer[0] == PAINT_MESSAGE):
            if(len(buffer) < 8):
                break
            x = to_int(buffer[1:3])
            y = to_int(buffer[3:5])
            r = to_int(buffer[5])
            g = to_int(buffer[6])
            b = to_int(buffer[7])
            handle_paint_message(x, y, r, g, b)
            del buffer[0:8]
        elif(buffer[0] == PAINT_RESULT):
            if(len(buffer) < 6):
                break
            id = to_int(buffer[1:5])
            status_code = to_int(buffer[5])
            if(status_code != SUCCESS):
                item = sended[id]
                work_list.add_work(item, True)
            print(f"[{gettime()}] receive painting result: [id={id} status_code={status_code}]")
            del(buffer[0:6])

# 发送消息
def sender(ws):
    global sender_buffer
    while(True):
        if not ws.sock or not ws.sock.connected:
            print("连接已断开，任务结束")
            break
        packet_size = min(len(sender_buffer), MAX_PACKET_SIZE)
        if(packet_size != 0):
            ws.send(
                sender_buffer[0:packet_size],
                websocket.ABNF.OPCODE_BINARY
            )
            if(packet_size < 1024):
                data_size = f"{packet_size}B"
            else:
                data_size = f"{packet_size / 1024}KB"
            print(f"[{gettime()}] 已发送 {data_size} 的数据")
            del sender_buffer[0:packet_size]
        time.sleep(SEND_INTERVAL)

# 提交任务到发送列表
def work_submitter(ws):
    global work_list, token_pool
    token_count = token_pool.count()
    while(True):
        if not ws.sock or not ws.sock.connected:
            print("连接已断开，任务结束")
            break
        wk = work_list.get_work()
        if(wk):
            draw_a_point(wk)
        time.sleep(CD / 1000 / token_count)

def on_open(ws):
    global executor
    print(f"[{gettime()}] 连接成功")
    executor.submit(sender, ws)
    executor.submit(work_submitter, ws)
    executor.submit(add_image)

# ------------------------ 添加图片至任务 ----------------------------

def add_image_to_work(filename:str, start_x:int, start_y:int, len_x:int, len_y:int):
    global all_board
    img = read_image(filename, len_x, len_y)
    all_board.insert_image(img, start_x, start_y)

# -------------------------------------------------------------------

def main():
    global token_pool, defend_map, app, START_X, START_Y, img, WS_URL, all_board
    
    # 读取 AccessKey 列表
    print(f"[{gettime()}] 正在读取 token 列表")
    access_key_list = []
    with open("token.json", "r", encoding="utf-8") as f:
        data = json.loads(f.read())
    for user in data["user_list"]:
        access_key_list.append((user["uid"], user["access_key"]))

    # 获取 token
    print(f"[{gettime()}] 正在获取 token")
    for uid, access_key in access_key_list:
        token = get_token(uid, access_key)
        if(token):
            token_pool.add_token(uid, token)
    print(f"[{gettime()}] 已获取 {token_pool.count()} 个 token")

    # 处理图片
    print(f"[{gettime()}] 正在处理图片")
    
    for file, start_x, start_y, len_x, len_y in IMAGE_LIST:
        add_image_to_work(file, start_x, start_y, len_x, len_y)

    defend_map.set_img(all_board)

    while(True):
        app = websocket.WebSocketApp(
            WS_URL,
            on_message=on_message,
            on_open=on_open
        )
        try:
            app.run_forever()
        except Exception as e:
            print(f"[{gettime()}] 已断连，尝试重连")
        time.sleep(5)

if __name__ == "__main__":
    main()
    
