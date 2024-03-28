import json
import os
import threading
import time
import uuid
from typing import TypedDict

import httpx
from fastapi import APIRouter, BackgroundTasks, Request

from arm.libs.openai_rpc import evaluate_text_friendly_level, rewrite_to_friendly_text

router = APIRouter()

cache = threading.local()

LEVEL_NAMES_MAP = {"A": "如沐春风", "B": "如水相安", "C": "剑拔弩张"}


class AccessToken(TypedDict):
    code: int  # 错误码，非 0 取值表示失败
    msg: str  # 错误描述
    tenant_access_token: str  # 租户访问凭证
    expire: int  # tenant_access_token 的过期时间，单位为秒, like 7200


class AccessTokenCache(TypedDict):
    expire_timestamp: int
    access_token: AccessToken


def _get_access_token():
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"

    response = httpx.post(
        url,
        headers={"Content-Type": "application/json"},
        json={"app_id": app_id, "app_secret": app_secret},
    )

    response.raise_for_status()

    return response.json()


def get_acccess_token() -> str:
    if not hasattr(cache, "access_token") or cache.access_token[
        "expire_timestamp"
    ] < int(time.time()):
        cache.access_token = {
            "expire_timestamp": int(time.time()) + 7200,
            "access_token": _get_access_token(),
        }
    return cache.access_token["access_token"]["tenant_access_token"]


def delete_msg(msg_id: str):
    url = f"https://open.feishu.cn/open-apis/im/v1/messages/{msg_id}"
    response = httpx.delete(
        url, headers={"Authorization": f"Bearer {get_acccess_token()}"}
    )
    content = response.text
    print(content)
    return


def check_if_make_new_group(data: dict):
    chat_type = data["event"]["message"]["chat_type"]
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
        headers={"Authorization": f"Bearer {get_acccess_token()}"},
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
        headers={"Authorization": f"Bearer {get_acccess_token()}"},
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
            "Authorization": f"Bearer {get_acccess_token()}",
            "Content-Type": "application/json",
        },
        params=params,
        data=payload,
    )
    content = response.text
    print(content)


def evaluate_and_rewrite_msg(data: dict):
    import time

    start = time.time()

    # sender_id = data["event"]["sender"]["sender_id"]["open_id"]

    event_type = data["header"]["event_type"]
    # chat_type = data["event"]["message"]["chat_type"]
    if event_type != "im.message.receive_v1":
        print("Not a message event")
        return
    text = json.loads(data["event"]["message"]["content"])["text"]
    level = evaluate_text_friendly_level(text)
    evaluate_end = time.time()
    print(f"evaluate cost: {evaluate_end - start}")
    if level in ["A", "B"]:
        print(f"Level {level}/({LEVEL_NAMES_MAP[level]})")
        return
    msg_id = data["event"]["message"]["message_id"]
    delete_msg(msg_id)
    output = rewrite_to_friendly_text(text)
    rewrite_end = time.time()
    print(f"rewrite cost: {rewrite_end - evaluate_end}")
    res = {"level": LEVEL_NAMES_MAP[level], "output": output}
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


@router.post("")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    print(body)
    data = json.loads(body)
    print(json.dumps(data, ensure_ascii=False))
    if "challenge" in data:
        return {"challenge": data["challenge"]}
    background_tasks.add_task(process_event, data)
    return {"message": "Webhook received"}
