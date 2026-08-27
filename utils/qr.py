import qrcode
import os
import io 
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL")

def generar_qr(token: str, tipo: str) -> bytes:
    """
    Genera un QR como bytes PNG listo para descargar
    """
    url = f"{BASE_URL}/asistencia/{tipo}?token={token}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4
    )

    qr.add_data(url)
    qr.make(fit=True)

    img= qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer.getvalue()
