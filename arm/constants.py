import os
import pathlib

# 需要设置的环境变量
FEISHU_APP_ID = os.environ["FEISHU_APP_ID"]
FEISHU_APP_SECRET = os.environ["FEISHU_APP_SECRET"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

NONCE_STR = "13oEviLbrTo458A3NjrOwS70oTOXVOAm"

TEMPLATE_DIR = pathlib.Path(__file__).absolute().parent / "templates"
