import requests
import json

BASE_URL = "paintboard.luogu.me"
GET_TOKEN_URL = f"https://{BASE_URL}/api/auth/gettoken"

class User:
    def __init__(self, username:str, uid:int, access_key:str, info:str):
        self.username = username
        self.uid = uid
        self.access_key = access_key
        self.info = info
        self.token = ""
    def get_token(self) -> bool:
        print(f"正在检查 uid:{self.uid} 的 AccessKey 有效性。")
        try:
            res = requests.post(
                GET_TOKEN_URL,
                json={
                    "uid": self.uid,
                    "access_key": self.access_key
                }
            )
            json_data = json.loads(res.text)
            data = json_data["data"]
            if(data.get("errorType") == "INVALID_ACCESS_KEY"):
                print("AccessKey 无效。")
                return False
            if(data.get("errorType") == "UID_MISMATCH"):
                print("UID 不匹配。")
                return False
            if(data.get("errorType") == "SERVER_ERROR"):
                print("服务器错误。")
                return False
            if(data.get("errorType") == "BAD_REQUEST"):
                print("请求格式错误。")
                return False
            if(data.get("token") == None):
                print("未返回 token。")
                return False
            self.token = data.get("token")
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def print_info(self):
        print(f"uid: {self.uid} 的 AccessKey 详情：")
        print(f"- 用户名：{self.username}")
        print(f"- AccessKey：{self.access_key}")
        print(f"- 来源信息：{self.info}")
        print()
        

def main():

    user_list = []
    user_count = 0
    check_count = 0
    pass_count = 0
    with open("token.json", "r", encoding="utf-8") as f:
        data = json.loads(f.read())
    for user in data["user_list"]:
        user_list.append(
            User(
                user["username"],
                user["uid"],
                user["access_key"],
                user["info"],
            )
        )
        user_count += 1
    for user in user_list:
        check_count += 1
        print(f"# {check_count} / {user_count}")
        if(user.get_token()):
            print("AccessKey 有效")
            pass_count += 1
        else:
            user.print_info()   
    
    print()
    print("已全部检测完成")
    print(f"总 AccessKey 数：{user_count}")
    print(f"有效 AccessKey 数：{pass_count}")

if __name__ == "__main__":
    main()