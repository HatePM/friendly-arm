import json
import time
import uuid

import httpx
from fastapi import APIRouter, BackgroundTasks, Request

from arm.libs.feishu_auth import FEISHU_AUTH
from arm.libs.openai_rpc import evaluate_text_friendly_level, rewrite_to_friendly_text

router = APIRouter()


def delete_msg(msg_id: str):
    url = f"https://open.feishu.cn/open-apis/im/v1/messages/{msg_id}"
    response = httpx.delete(
        url,
        headers={"Authorization": f"Bearer {FEISHU_AUTH.get_tenant_access_token()}"},
    )
    content = response.text
    print(content)
    return


def check_if_make_new_group(data: dict):
    chat_type = data["event"]["message"]["chat_type"]
    event_type = data["header"]["event_type"]
    chat_type = data["event"]["message"]["chat_type"]
    message_type = data["event"]["message"]["message_type"]
    if event_type != "im.message.receive_v1" or chat_type != "group" or message_type != "text":
        print("Not a message event")
        return
    content = json.loads(data["event"]["message"]["content"])["text"]
    print(chat_type, content)
    if chat_type == "p2p" and content == "/new_group":
        return True
    return False


def make_new_group(data: dict):
    url = "https://open.feishu.cn/open-apis/im/v1/chats"
    params = {
        "user_id_type": "open_id",
        "set_bot_manager": "true",
    }
    body = {
        "user_id_list": [data["event"]["sender"]["sender_id"]["open_id"]],
    }
    response = httpx.post(
        url,
        headers={"Authorization": f"Bearer {FEISHU_AUTH.get_tenant_access_token()}"},
        params=params,
        json=body,
    )
    body = response.json()
    print(body)


def get_user_info(open_id: str):
    url = f"https://open.feishu.cn/open-apis/contact/v3/users/{open_id}"
    params = {
        "user_id_type": "open_id",
    }
    response = httpx.get(
        url,
        headers={"Authorization": f"Bearer {FEISHU_AUTH.get_tenant_access_token()}"},
        params=params,
    )
    body = response.json()
    print(body)
    return body  # ["data"]["user"]["name"]


def send_msg(data: dict, text: str):
    chat_id = data["event"]["message"]["chat_id"]
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": "chat_id"}
    user_id = data["event"]["sender"]["sender_id"]["open_id"]
    user_name = get_user_info(user_id)["data"]["user"]["name"]
    body = {
        "receive_id": chat_id,
        "msg_type": "text",
        "content": json.dumps(
            {"text": f"{user_name}: {text}"},
        ),
        "uuid": str(uuid.uuid4()),
    }
    payload = json.dumps(body)
    print(payload)
    response = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {FEISHU_AUTH.get_tenant_access_token()}",
            "Content-Type": "application/json",
        },
        params=params,
        data=payload,
    )
    content = response.text
    print(content)


def evaluate_and_rewrite_msg(data: dict):

    start = time.time()

    # sender_id = data["event"]["sender"]["sender_id"]["open_id"]

    event_type = data["header"]["event_type"]
    chat_type = data["event"]["message"]["chat_type"]
    message_type = data["event"]["message"]["message_type"]
    if event_type != "im.message.receive_v1" or chat_type != "group" or message_type != "text":
        print("Not a message event")
        return
    text = json.loads(data["event"]["message"]["content"])["text"]
    level = evaluate_text_friendly_level(text)
    evaluate_end = time.time()
    print(f"evaluate cost: {evaluate_end - start}")
    if level in ["A", "B"]:
        print(f"Level {level})")
        return
    msg_id = data["event"]["message"]["message_id"]
    delete_msg(msg_id)
    output = rewrite_to_friendly_text(text)
    rewrite_end = time.time()
    print(f"rewrite cost: {rewrite_end - evaluate_end}")
    res = {"level": level, "output": output}
    print(res)
    send_msg(data, output)
    end = time.time()
    print(f"total cost: {end - start}")
    return


def process_event(data: dict):
    if check_if_make_new_group(data):
        make_new_group(data)
        return
    evaluate_and_rewrite_msg(data)


@router.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    print(body)
    data = json.loads(body)
    print(json.dumps(data, ensure_ascii=False))
    if "challenge" in data:
        return {"challenge": data["challenge"]}
    background_tasks.add_task(process_event, data)
    return {"message": "Webhook received"}
