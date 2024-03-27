from fastapi import Body, FastAPI
from fastapi.responses import HTMLResponse
from pydantic import constr

from arm.rpc import evaluate_and_rewrite_text

app = FastAPI(title="FriendlyArm")
LEVEL_NAMES_MAP = {"A": "如沐春风", "B": "如水相安", "C": "剑拔弩张"}


@app.get("/", response_class=HTMLResponse)
def render_html():
    return """
    <html>
    <head>
        <title>友善之臂</title>
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script>
            $(document).ready(function() {
                $("#myForm").submit(function(event) {
                    event.preventDefault();
                    var formData = {
                        "text": $("#myTextArea").val()
                    };
                    $.ajax({
                        type: "POST",
                        url: "/api/submit",
                        data: JSON.stringify(formData),
                        contentType: "application/json",
                        success: function(response) {
                            $("#outputTextArea").val(response.output);
                            $("#levelText").text(response.level);
                        },
                        error: function(error) {
                            console.log(error);
                        }
                    });
                });
            });
        </script>
    </head>
    <body>
        <form id="myForm">
            <textarea id="myTextArea" rows="4" cols="50"></textarea>
            <br>
            <input type="submit" value="Submit">
        </form>
        <br>
        <div id="levelText"></div>
        <textarea id="outputTextArea" rows="4" cols="50" readonly></textarea>
    </body>
    </html>
    """


@app.post("/api/submit")
def submit(text: constr(strip_whitespace=True) = Body(..., embed=True)):
    level, output = evaluate_and_rewrite_text(text)

    return {"level": LEVEL_NAMES_MAP[level], "output": output}
