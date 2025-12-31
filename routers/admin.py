from fastapi import APIRouter, Request, Form, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, StreamingResponse, HTMLResponse  # HTMLResponse 추가
from models import Booth, Survey
import pandas as pd
from io import BytesIO
from services.qr_service import generate_booth_qr
from uuid import UUID

router = APIRouter(prefix="/booth", tags=["booth"])
templates = Jinja2Templates(directory="templates")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "dmubestbooth3#"
COOKIE_KEY = "admin_session"
COOKIE_VALUE = "valid_admin"


def check_admin_auth(request: Request):
    token = request.cookies.get(COOKIE_KEY)
    if token != COOKIE_VALUE:
        return False
    return True


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # 이미 로그인 되어있으면 관리자 페이지로
    if check_admin_auth(request):
        return RedirectResponse(url="/booth/admin", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        # 로그인 성공! -> 쿠키 굽기 (24시간 유지)
        redirect_url = "/booth/admin"
        res = RedirectResponse(url=redirect_url, status_code=302)
        res.set_cookie(key=COOKIE_KEY, value=COOKIE_VALUE, max_age=60 * 60 * 24)
        return res
    else:
        # 로그인 실패 -> 에러 메시지
        return templates.TemplateResponse("login.html", {"request": request, "error": "아이디 또는 비밀번호가 틀렸습니다."})


@router.get("/logout")
async def logout():
    # 로그아웃 -> 쿠키 삭제 후 로그인 페이지로
    res = RedirectResponse(url="/booth/login", status_code=302)
    res.delete_cookie(COOKIE_KEY)
    return res


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    # 1. 모든 부스 가져오기 (최신순 정렬)
    if not check_admin_auth(request):
        return RedirectResponse(url="/booth/login", status_code=302)

    booths = await Booth.find_all().sort("-created_at").to_list()

    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "booths": booths}
    )


@router.post("/admin/create_booth")
async def create_booth(request: Request, name: str = Form(...), location: str = Form(""), description: str = Form("")):
    """
    부스 생성 -> DB 저장 -> QR 생성 -> 업데이트
    """
    if not check_admin_auth(request): return RedirectResponse(url="/booth/login", status_code=302)

    new_booth = Booth(name=name, location=location, description=description)
    await new_booth.insert()

    domain_url = str(request.base_url).rstrip("/")

    # QR 생성 (qr_service.py에 generate_booth_qr 함수가 있어야 함)
    qr_path = generate_booth_qr(new_booth.booth_id, name, domain_url)

    new_booth.qr_image_path = qr_path
    await new_booth.save()

    return RedirectResponse(url="/booth/admin", status_code=303)


@router.post("/admin/delete/{booth_uuid}")
async def delete_booth(request: Request, booth_uuid: str):
    if not check_admin_auth(request): return RedirectResponse(url="/booth/login", status_code=302)

    # 해당 ID를 가진 부스를 찾아서 삭제
    booth = await Booth.find_one(Booth.booth_id == UUID(booth_uuid))
    if booth:
        await booth.delete()

    return RedirectResponse(url="/booth/admin", status_code=303)


@router.post("/admin/update/{booth_uuid}")
async def update_booth(
        request: Request,
        booth_uuid: str,
        name: str = Form(...),
        description: str = Form(""),  # 내용 없으면 빈칸
        location: str = Form("")
):
    if not check_admin_auth(request): return RedirectResponse(url="/booth/login", status_code=302)
    booth = await Booth.find_one(Booth.booth_id == UUID(booth_uuid))
    if booth:
        # 내용 업데이트
        booth.name = name
        booth.description = description
        booth.location = location
        await booth.save()  # DB에 저장

    return RedirectResponse(url="/booth/admin", status_code=303)


@router.get("/admin/export_excel")
async def export_excel(request: Request):
    if not check_admin_auth(request): return RedirectResponse(url="/booth/login", status_code=302)

    booths = await Booth.find_all().to_list()

    data = []
    for booth in booths:
        data.append({
            "부스 이름": booth.name,
            "위치": booth.location,
            "총 방문자 수": booth.total_visits,
            "평균 평점": round(booth.avg_score, 2),  # 소수점 2자리
            "설명": booth.description
        })

    # 데이터프레임 생성
    df = pd.DataFrame(data)

    # 엑셀 파일로 변환
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='부스결과')

    output.seek(0)

    headers = {
        'Content-Disposition': 'attachment; filename="festival_result.xlsx"'
    }

    return StreamingResponse(output, headers=headers,
                             media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@router.post("/admin/reset_all")
async def reset_all_data(request: Request):
    if not check_admin_auth(request): return RedirectResponse(url="/booth/login", status_code=302)
    # 1. 모든 설문(투표) 데이터 삭제
    await Survey.delete_all()

    await Booth.delete_all()

    return RedirectResponse(url="/booth/admin", status_code=303)
