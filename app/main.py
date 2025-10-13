from fastapi import FastAPI
from app.routes.user_routes import router as user_router
from app.routes.planner_routes import router as planner_router
from app.routes.admin_routes import router as admin_router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router)
app.include_router(planner_router)
app.include_router(admin_router)
