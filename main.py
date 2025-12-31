from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import os
from database import init_db
from routers import user, admin, analysis

# --- [Lifespan: 앱 생명주기 관리] ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 시작 시: DB 연결
    await init_db()
    print("MongoDB Connected via Beanie!")

    # 2. QR 코드 저장 폴더 자동 생성 (없으면 에러나니까)
    qr_path = "static/qrcodes"
    if not os.path.exists(qr_path):
        os.makedirs(qr_path)
        print(f"Created directory: {qr_path}")

    yield
    # 3. 종료 시: (필요하면 연결 종료 로직 추가)
    print("App Shutdown")

origins = [
    "http://localhost",
    "http://localhost:3000", # 리액트 등 프론트엔드 포트
    "http://127.0.0.1:8000",
    "https://campuslife.dongyang.ac.kr",
    "http://campuslife.dongyang.ac.kr"
]

# 앱 초기화
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # 허용할 출처 목록
    allow_credentials=True,     # 쿠키(세션) 포함 허용 (매우 중요! set_cookie 때문에 필수)
    allow_methods=["*"],        # 허용할 HTTP 메서드 (GET, POST, PUT, DELETE 등 전체)
    allow_headers=["*"],        # 허용할 HTTP 헤더 (Content-Type, Authorization 등 전체)
)

app.include_router(user.router)
app.include_router(admin.router)
app.include_router(analysis.router)

# --- [정적 파일 및 템플릿 설정] ---
# /booth/static 경로로 들어오는 요청은 static 폴더의 파일을 보여줌
app.mount("/booth/static", StaticFiles(directory="static"), name="static")

# templates 폴더를 Jinja2 템플릿 경로로 지정
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def root():
    return "main"
