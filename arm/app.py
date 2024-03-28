import pathlib

from fastapi import Body, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import constr

from arm.rpc import evaluate_and_rewrite_text

app = FastAPI(title="FriendlyArm")
LEVEL_NAMES_MAP = {
    "A": "<span class='label label-success'>如沐春风</span>",
    "B": "<span class='label label-warning'>如水相安</span>",
    "C": "<span class='label label-danger'>剑拔弩张</span>",
}
TEMPLATE_DIR = pathlib.Path(__file__).absolute().parent / "templates"


@app.get("/", response_class=HTMLResponse)
def render_html(request: Request):

    amis_schema = [
        {
            "type": "form",
            "title": "输入",
            "api": "/api/submit",
            "reload": "resultForm?level=${level}&output=${output}",
            "autoFocus": True,
            "actions": [{"type": "submit", "label": "Magic🪄", "level": "light"}],
            "body": [
                {
                    "name": "text",
                    "type": "textarea",
                    "required": True,
                    "trimContents": True,
                    "showCounter": True,
                    "maxLength": 100,
                    "placeholder": "请在此输入你想说的话",
                },
            ],
        },
        {
            "name": "resultForm",
            "type": "form",
            "title": "输出",
            "body": [
                {
                    "label": "友善度评级",
                    "name": "level",
                    "type": "static-mapping",
                    "map": LEVEL_NAMES_MAP,
                },
                {
                    "label": "重写结果",
                    "name": "output",
                    "type": "textarea",
                    "trimContents": True,
                    "description": "如果对友善之臂的输出结果不满意，可自由修改",
                },
            ],
            "actions": [],
        },
    ]
    return Jinja2Templates(directory=TEMPLATE_DIR).TemplateResponse(
        name="plus_menu_shortcut.html.jinja",
        context={"request": request, "amis_schema": amis_schema},
    )


@app.post("/api/submit")
def submit(text: constr(strip_whitespace=True) = Body(..., embed=True)):
    level, output = evaluate_and_rewrite_text(text)
    return {"level": level, "output": output}
