from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from services.analysis_service import calculate_trimmed_mean_logic, generate_report_logic, df_to_excel, get_merged_report_df
from fastapi.templating import Jinja2Templates
import pandas as pd
import io

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.get("/", response_class=HTMLResponse)
async def analysis_page(request: Request):
    """역량 분석 도구 페이지 렌더링"""
    return templates.TemplateResponse("analysis.html", {"request": request})


# 1. [미리보기용] JSON 데이터 반환
@router.post("/calc-average/preview")
async def calculate_average_preview(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="엑셀 파일만 업로드 가능합니다.")

    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))

        # 계산 로직 실행
        result_df = calculate_trimmed_mean_logic(df)

        # DataFrame -> Dictionary 변환 (JSON 응답용)
        # orient='split'은 index, columns, data를 분리해서 줍니다.
        return result_df.to_dict(orient='split')

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"계산 중 오류 발생: {str(e)}")


# 2. [다운로드용] 엑셀 파일 반환
@router.post("/calc-average/download")
async def calculate_average_download(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="엑셀 파일만 업로드 가능합니다.")

    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))

        # 계산 로직 실행
        result_df = calculate_trimmed_mean_logic(df)

        # 엑셀 변환
        output_excel = df_to_excel(result_df)

        return StreamingResponse(
            output_excel,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': 'attachment; filename="average_result.xlsx"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"다운로드 중 오류 발생: {str(e)}")


@router.post("/generate-report/preview")
async def generate_report_preview(
        my_file: UploadFile = File(...),
        others_file: UploadFile = File(...)
):
    try:
        # 파일 읽기
        my_content = await my_file.read()
        others_content = await others_file.read()

        # DataFrame 병합 로직 실행
        df_merged = get_merged_report_df(io.BytesIO(my_content), io.BytesIO(others_content))

        # JSON 변환 (index=False)
        return df_merged.to_dict(orient='split')

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 병합 중 오류: {str(e)}")


# 2. [다운로드] 차트 포함 엑셀 파일 생성 (기존 로직)
@router.post("/generate-report/download")
async def generate_report_download(
        my_file: UploadFile = File(...),
        others_file: UploadFile = File(...)
):
    try:
        my_content = await my_file.read()
        others_content = await others_file.read()

        # 기존의 엑셀+차트 생성 로직 실행 (시간이 좀 걸림)
        output_excel = generate_report_logic(io.BytesIO(my_content), io.BytesIO(others_content))

        return StreamingResponse(
            output_excel,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': 'attachment; filename="final_report.xlsx"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리포트 생성 중 오류: {str(e)}")
