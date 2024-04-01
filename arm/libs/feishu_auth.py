import time

import httpx
from pydantic import BaseModel

from arm.constants import FEISHU_APP_ID, FEISHU_APP_SECRET


class TenantAccessTokenCache(BaseModel):
    expired_at: int
    token: str


class JSSDKTicketCache(BaseModel):
    expired_at: int
    ticket: str


class FeishuAuth(object):
    def __init__(self, app_id, app_secret):
        self.app_id = app_id
        self.app_secret = app_secret
        self._tenant_access_token_cache = None
        self._jssdk_ticket_cache = None
        self.get_tenant_access_token()
        self.get_jssdk_ticket()

    def _get_tenant_access_token(self):
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        response = httpx.post(
            url,
            json={"app_id": self.app_id, "app_secret": self.app_secret},
        )
        response.raise_for_status()
        # {
        #     "code": 0,
        #     "msg": "ok",
        #     "tenant_access_token": "t-caecc734c2e3328a62489fe0648c4b98779515d3",
        #     "expire": 7200,
        # }
        return response.json()

    def get_tenant_access_token(self) -> str:
        now = int(time.time())
        if (
            self._tenant_access_token_cache
            and self._tenant_access_token_cache.expired_at > now
        ):
            return self._tenant_access_token_cache.token
        token_data = self._get_tenant_access_token()
        self._tenant_access_token_cache = TenantAccessTokenCache(
            expired_at=now + token_data["expire"] - 100,
            token=token_data["tenant_access_token"],
        )
        return self._tenant_access_token_cache.token

    def _get_jssdk_ticket(self):
        url = "https://open.feishu.cn/open-apis/jssdk/ticket/get"
        headers = {
            "Authorization": "Bearer " + self.get_tenant_access_token(),
            "Content-Type": "application/json",
        }
        resp = httpx.post(url=url, headers=headers)
        resp.raise_for_status()
        # {
        #     "code": 0,
        #     "msg": "ok",
        #     "data": {
        #         "expire_in": 7200,
        #         "ticket": "0560604568baf296731aa37f0c8ebe3e049c19d7",
        #     },
        # }
        return resp.json()["data"]

    def get_jssdk_ticket(self) -> str:
        now = int(time.time())
        if self._jssdk_ticket_cache and self._jssdk_ticket_cache.expired_at > now:
            return self._jssdk_ticket_cache.ticket
        ticket_data = self._get_jssdk_ticket()
        self._jssdk_ticket_cache = JSSDKTicketCache(
            expired_at=now + ticket_data["expire_in"] - 100,
            ticket=ticket_data["ticket"],
        )
        return self._jssdk_ticket_cache.ticket


FEISHU_AUTH = FeishuAuth(app_id=FEISHU_APP_ID, app_secret=FEISHU_APP_SECRET)
