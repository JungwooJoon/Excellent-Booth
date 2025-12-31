from typing import Optional
from uuid import UUID, uuid4
from typing import Annotated
from datetime import datetime
from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


# 1. 부스 정보 모델
class Booth(Document):
    # UUID: URL에 노출될 보안 ID (자동생성, 유니크 인덱스)
    booth_id: Annotated[UUID, Indexed(unique=True)] = Field(default_factory=uuid4)
    name: str

    location: str = ""
    description: str = ""

    total_visits: int = 0
    total_score: int = 0

    description: Optional[str] = None
    qr_image_path: Optional[str] = None  # QR 이미지 파일 경로

    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def avg_score(self) -> float:
        if self.total_visits == 0:
            return 0.0
        return self.total_score / self.total_visits

    class Settings:
        name = "booths"


# 2. 설문 응답 모델
class Survey(Document):
    id: UUID = Field(default_factory=uuid4)
    booth_id: Annotated[UUID, Indexed()]
    score: int

    # [방어 1단계] 쿠키 ID (기존 voter_id 유지)
    voter_id: Annotated[str, Indexed()]

    # [방어 2단계] 기기 고유 지문 (새로 추가!)
    fingerprint: Annotated[str, Indexed()]

    created_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "surveys"