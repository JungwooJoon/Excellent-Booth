import qrcode
from PIL import Image, ImageDraw, ImageFont
import os
from uuid import UUID

# QR 저장 경로
QR_PATH = "static/qrcodes"
FONT_PATH = "static/fonts/malgunbd.ttf"


def generate_booth_qr(booth_id: UUID, booth_name: str, domain_url: str):
    """
    부스 UUID를 받아 QR 코드를 생성하고 파일로 저장합니다.
    QR 내용: http://도메인/entry/{uuid}
    """
    # 1. 실제 접속할 URL 생성
    if not os.path.exists(QR_PATH):
        os.makedirs(QR_PATH)

        # 1. 실제 접속할 URL 생성
    domain_url = domain_url.rstrip("/")
    target_url = f"{domain_url}/booth/entry/{booth_id}"

    # 2. QR 코드 객체 생성
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # 글자가 들어가므로 보정율 높임
        box_size=10,
        border=2,  # 테두리는 얇게 (글씨 공간 확보)
    )
    qr.add_data(target_url)
    qr.make(fit=True)

    # 3. 기본 QR 이미지 생성 (RGB 모드로 변환해야 컬러/텍스트 작업 가능)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

    # (1) 폰트 로드
    try:
        # static/fonts/font.ttf 경로에 한글 폰트가 있어야 함
        if os.path.exists(FONT_PATH):
            font = ImageFont.truetype(FONT_PATH, 24)  # 폰트 크기 24
        else:
            # 윈도우/맥 기본 폰트 시도 (개발 환경용 fallback)
            font = ImageFont.truetype("malgun.ttf", 24)
    except:
        print("⚠️ 폰트를 찾을 수 없어 기본 폰트를 사용합니다. (한글 깨짐 가능성 있음)")
        font = ImageFont.load_default()

    # (2) 캔버스 확장 (QR 높이 + 텍스트 공간 60px)
    qr_w, qr_h = qr_img.size
    padding_bottom = 60
    new_h = qr_h + padding_bottom

    # 흰색 배경의 새 이미지 생성
    new_img = Image.new("RGB", (qr_w, new_h), "white")

    # 위쪽에 QR 코드 붙여넣기
    new_img.paste(qr_img, (0, 0))

    # (3) 텍스트 그리기 (가운데 정렬)
    draw = ImageDraw.Draw(new_img)

    # 텍스트 크기 측정 (Pillow 10.0.0 이상: textbbox 사용)
    # bbox = (left, top, right, bottom)
    bbox = draw.textbbox((0, 0), booth_name, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # 좌표 계산
    x = (qr_w - text_w) / 2
    # y = QR높이 + (남은공간 - 글자높이)/2
    y = qr_h + (padding_bottom - text_h) / 2 - 5

    # 글씨 쓰기
    draw.text((x, y), booth_name, fill="black", font=font)

    # --- [텍스트 추가 로직 끝] ---

    # 4. 파일 저장 (파일명은 UUID로 하여 유니크하게 관리)
    file_path = os.path.join(QR_PATH, f"{booth_id}.png")
    new_img.save(file_path)

    # 웹에서 접근 가능한 경로 반환 (/booth 서브경로 포함)
    return f"/booth/static/qrcodes/{booth_id}.png"
