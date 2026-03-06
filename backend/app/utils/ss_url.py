import base64
import io

import qrcode


def generate_ss_url(method: str, password: str, host: str, port: int, tag: str = "VPN") -> str:
    userinfo = f"{method}:{password}"
    encoded = base64.urlsafe_b64encode(userinfo.encode()).decode().rstrip("=")
    return f"ss://{encoded}@{host}:{port}#{tag}"


def generate_qr_base64(data: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode()
    return f"data:image/png;base64,{encoded}"
