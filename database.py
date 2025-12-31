import os
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from dotenv import load_dotenv
from models import Booth, Survey  # 우리가 만든 모델 불러오기

# .env 파일 로드
load_dotenv()


async def init_db():
    # 1. 환경 변수에서 DB 주소 가져오기
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    db_name = os.getenv("DB_NAME", "festival_db")

    # 2. Motor 클라이언트 생성 (비동기)
    client = AsyncIOMotorClient(mongo_url)

    # 3. 데이터베이스 선택
    database = client[db_name]

    # 4. Beanie 초기화 (모델 등록)
    # document_models에 등록된 클래스들은 자동으로 MongoDB 컬렉션과 매핑됨
    await init_beanie(database=database, document_models=[Booth, Survey])