from fastapi import FastAPI

from arm.views.group_bot import router as group_bot_router
from arm.views.plus_menu import router as plus_menu_router

app = FastAPI(title="FriendlyArm")

app.include_router(group_bot_router, prefix="/group_bot", tags=["Group Bot"])
app.include_router(plus_menu_router, prefix="/plus_menu", tags=["Plus Menu"])
