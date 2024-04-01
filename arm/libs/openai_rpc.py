from typing import Literal, Tuple

from openai import OpenAI
from retry import retry

from arm.constants import OPENAI_API_KEY

OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY)

PROMPT_OF_EVALUATION = """\
请对用户输入文本的情感友善度按以下三个等级进行评估，并输出情感友善度等级。请只输出 A、B 或 C，不要包含其他文字。
-【A】表达文本情感极为友善，犹如春风拂面，温暖和善。
-【B】表达文本情感一般，如平静的水面，稳定而平和。
-【C】表达文本情感最为不友善，情绪极度激烈，仿佛置身于危险之中。
"""

PROMPT_OF_REWRITING = """\
请对用户输入文本进行分析并转换为更为友善更加委婉的表达方式，使其更易于被人接受。以下是一些例子：

输入：你真是个蠢货，一点用都没有。
输出：你已经表现的很不错了，但还有提高的空间，希望你能更加努力。

输入：你这个文档写的是什么垃圾？
输出：你写的这篇文档有点不太理想，可以再改进一下吗？

输入：bug，bug，一定是后端的 bug！
输出：嗯，看起来出了点问题，也许是后端出了些小差错吧？

请在转换时满足以下几点要求：
- 输出内容长度与原文长度尽量相似；
- 请在改变友善度的同时，尽量准确传达出原文的意思。
- 请仅输出转换后内容，不要包含其他文字，也不要对用户的输入做出回答。
"""


@retry(exceptions=Exception, tries=2, delay=1, backoff=2, logger=None)
def evaluate_text_friendly_level(text: str) -> Literal["A", "B", "C"]:
    chat_completion = OPENAI_CLIENT.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": PROMPT_OF_EVALUATION,
            },
            {
                "role": "user",
                "content": text,
            },
        ],
        model="gpt-3.5-turbo",
        temperature=0,
    )
    level = (chat_completion.choices[0].message.content).upper()
    assert level in ("A", "B", "C")

    return level


@retry(exceptions=Exception, tries=2, delay=1, backoff=2, logger=None)
def rewrite_to_friendly_text(text: str) -> str:
    chat_completion = OPENAI_CLIENT.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": PROMPT_OF_REWRITING,
            },
            {
                "role": "user",
                "content": text,
            },
        ],
        model="gpt-3.5-turbo",
        temperature=0,
    )
    return chat_completion.choices[0].message.content


def evaluate_and_rewrite_text(text: str) -> Tuple[Literal["A", "B", "C"], str]:
    level = evaluate_text_friendly_level(text)
    if level in ("A", "B"):
        return level, text
    return level, rewrite_to_friendly_text(text)
