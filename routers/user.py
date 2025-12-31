from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse
from models import Booth, Survey
from uuid import UUID, uuid4
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError
from beanie.operators import Or

router = APIRouter(prefix="/booth", tags=["booth"])
templates = Jinja2Templates(directory="templates")


class SurveyRequest(BaseModel):
    booth_id: str
    score: int
    fingerprint: str


@router.get("/success")
async def success_page(request: Request):
    return templates.TemplateResponse("success.html", {"request": request})

# 1. QR 찍고 들어왔을 때 -> 신분 선택 페이지(select_type.html) 보여줌
@router.get("/entry/{booth_id}")
async def entry_page(request: Request, booth_id: str):
    # 부스가 진짜 있는지 확인}
    try:
        booth = await Booth.find_one(Booth.booth_id == UUID(booth_id))
        if not booth:
            return templates.TemplateResponse("error.html", {"request": request, "msg": "유효하지 않은 부스입니다."})

        return templates.TemplateResponse(
            "select_type.html",
            {"request": request, "booth_id": booth_id,"booth": booth}
        )
    except ValueError:
        # UUID 형식이 아닌 이상한 문자열이 들어왔을 때의 예외 처리
        return templates.TemplateResponse("error.html", {"request": request, "msg": "잘못된 부스 ID 형식입니다."})


# 2. 신분 선택 후 -> 설문조사 페이지(survey.html)로 이동
@router.get("/survey/{booth_uuid}")
async def get_survey_page(request: Request, booth_uuid: str):
    # 1. 부스가 진짜 있는지 확인 (선택 사항이지만 안전을 위해 권장)
    try:
        booth = await Booth.find_one(Booth.booth_id == UUID(booth_uuid))
        if not booth:
            return templates.TemplateResponse("error.html", {"request": request, "msg": "존재하지 않는 부스입니다."})
    except:
        return templates.TemplateResponse("error.html", {"request": request, "msg": "잘못된 주소입니다."})

    # 2. survey.html 화면을 보여줌
    return templates.TemplateResponse("survey.html", {"request": request,"booth": booth})


@router.post("/survey/{booth_uuid}")
async def submit_survey(booth_uuid: str, survey_data: SurveyRequest, request: Request):
    try:
        # [방어 1] 쿠키 확인
        cookie_id = request.cookies.get("fbs_voter")
        if not cookie_id:
            cookie_id = str(uuid4())  # 없으면 생성
            is_new_cookie = True
        else:
            is_new_cookie = False

        existing_vote = await Survey.find_one(
            Survey.booth_id == UUID(booth_uuid),
            Or(
                Survey.voter_id == cookie_id,
                Survey.fingerprint == survey_data.fingerprint
            )
        )

        if existing_vote:
            return JSONResponse(
                content={"status": "error", "msg": "이미 참여한 기기입니다!"}
            )

        # 저장
        await Survey(
            booth_id=UUID(booth_uuid),
            score=survey_data.score,
            voter_id=cookie_id,
            fingerprint=survey_data.fingerprint  # 지문도 같이 저장
        ).insert()

        response = JSONResponse(content={"status": "success", "msg": "제출되었습니다!"})

        # 쿠키 굽기 (3일)
        if is_new_cookie:
            response.set_cookie(key="fbs_voter", value=cookie_id, max_age=259200)

        return response

    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(content={"status": "error", "msg": "오류 발생"})


# 3. 설문 데이터 저장하기 (POST)
@router.post("/submit")
async def submit_survey(request: Request, survey_data: SurveyRequest):
    try:
        # [1] 쿠키 확인 및 생성 준비
        cookie_id = request.cookies.get("fbs_voter")
        is_new_cookie = False

        if not cookie_id:
            cookie_id = str(uuid4())
            is_new_cookie = True

        target_booth_uuid = UUID(survey_data.booth_id)

        # [2] DB 중복 검사 (쿠키 ID or 지문)
        existing_vote = await Survey.find_one(
            Survey.booth_id == target_booth_uuid,
            Or(
                Survey.voter_id == cookie_id,
                Survey.fingerprint == survey_data.fingerprint
            )
        )

        # ★ 중복일 경우 에러 JSON 반환
        if existing_vote:
            return JSONResponse(content={"status": "error", "msg": "이미 참여하셨습니다!"})

        # [3] 투표 정보 저장
        await Survey(
            booth_id=target_booth_uuid,
            score=survey_data.score,
            voter_id=cookie_id,
            fingerprint=survey_data.fingerprint
        ).insert()

        # [4] 부스 통계 업데이트 ($inc 사용)
        booth = await Booth.find_one(Booth.booth_id == target_booth_uuid)
        if booth:
            await booth.update({
                "$inc": {
                    "total_visits": 1,
                    "total_score": survey_data.score
                }
            })

        # [5] ★ JSON 응답 반환 (HTML 아님)
        response = JSONResponse(content={"status": "success", "msg": "제출되었습니다!"})

        # ★ 쿠키 굽기 (response 객체에 설정 후 그대로 리턴)
        if is_new_cookie:
            response.set_cookie(key="fbs_voter", value=cookie_id, max_age=259200)

        return response

    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(content={"status": "error", "msg": "서버 오류가 발생했습니다."}, status_code=500)