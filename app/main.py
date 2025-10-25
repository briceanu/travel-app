from fastapi import FastAPI, Request, status, Response
from app.routes.user_routes import router as user_router
from app.routes.planner_routes import router as planner_router
from app.routes.admin_routes import router as admin_router
from fastapi.middleware.cors import CORSMiddleware
from app.utils.logger import logger
import time
from pyinstrument import Profiler
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.utils.rate_limiter import limiter
from starlette.middleware.base import BaseHTTPMiddleware


app = FastAPI()

# profiling middleware


@app.middleware('http')
async def check_profile(request: Request, call_next):
    profiler = Profiler()
    profiler.start()
    response = await call_next(request)
    profiler.stop()
    logger.info(profiler.output_text(unicode=True, color=True))
    return response


@app.middleware('http')
async def total_end_point_execution(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    total_s = time.perf_counter() - start_time
    total_ms = total_s * 1000
    color = "\033[92m" if total_ms < 200 else "\033[93m" if total_ms < 1000 else "\033[91m"
    logger.info(
        f"{color}[ENDPOINT EXECUTION TIME: {total_ms:.2f} ms]{'\033[0m'} "
        f"{request.method} {request.url.path}"
    )
    return response


# class MyMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request, call_next):
#         profiler = Profiler()
#         profiler.start()
#         response = await call_next(request)
#         profiler.stop()
#         logger.info(profiler.output_text(unicode=True, color=True))
#         return response


# class TotalTime(BaseHTTPMiddleware):
#     async def dispatch(self, request, call_next):
#         start_time = time.perf_counter()
#         response = await call_next(request)
#         end_time = time.perf_counter() - start_time
#         logger.info(f'total time is: {end_time}')
#         return response


# app.add_middleware(MyMiddleware)
# app.add_middleware(TotalTime)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# add rate limit
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# routes

app.include_router(user_router)
app.include_router(planner_router)
app.include_router(admin_router)
