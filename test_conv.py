import clay_lib
import json

def test():
    urls = [
        "https://api.clay.com/v3/workspaces/744216/chat-conversations",
        "https://api.clay.com/v3/chat-conversations",
        "https://api.clay.com/v3/conversations",
        "https://api.clay.com/v3/chats",
        "https://api.clay.com/v3/workspaces/744216/chats",
        "https://api.clay.com/v3/workspaces/744216/conversations",
    ]
    for url in urls:
        res = clay_lib._post(url, {"workspaceId": 744216, "name": "Search"})
        print(url, "->", res[:150])

if __name__ == "__main__":
    test()
