import os 
from dotenv import load_dotenv
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from fastapi import HTTPException
from datetime import date
from models.email_quota import EmailQuota
from sqlalchemy.orm import Session

load_dotenv()

mail_config = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=False
)

def _html_pin(pin: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0; padding:0; background-color:#f4f4f4; font-family:Arial, sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f4; padding:40px 0;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:8px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.1);">
                        
                        <!-- HEADER -->
                        <tr>
                            <td style="background-color:#1a3a5c; padding:30px; text-align:center;">
                                <h1 style="color:#ffffff; margin:0; font-size:24px; letter-spacing:1px;">ASEBEP</h1>
                                <p style="color:#a8c4e0; margin:6px 0 0 0; font-size:13px;">Sistema de Gestión de Horas</p>
                            </td>
                        </tr>

                        <!-- BODY -->
                        <tr>
                            <td style="padding:40px 40px 20px 40px;">
                                <h2 style="color:#1a3a5c; margin:0 0 16px 0; font-size:20px;">Activación de cuenta</h2>
                                <p style="color:#555555; font-size:15px; line-height:1.6; margin:0 0 24px 0;">
                                    Recibimos una solicitud para activar tu cuenta en el sistema ASEBEP. 
                                    Usa el siguiente PIN para completar el proceso:
                                </p>

                                <!-- PIN BOX -->
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td align="center" style="padding:20px 0;">
                                            <div style="display:inline-block; background-color:#f0f5ff; border:2px dashed #1a3a5c; border-radius:8px; padding:20px 40px;">
                                                <p style="margin:0; font-size:13px; color:#777777; letter-spacing:1px; text-transform:uppercase;">Tu PIN de activación</p>
                                                <p style="margin:8px 0 0 0; font-size:42px; font-weight:bold; color:#1a3a5c; letter-spacing:8px;">{pin}</p>
                                            </div>
                                        </td>
                                    </tr>
                                </table>

                                <!-- EXPIRY WARNING -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="margin:20px 0;">
                                    <tr>
                                        <td style="background-color:#fff8e1; border-left:4px solid #f5a623; border-radius:4px; padding:14px 18px;">
                                            <p style="margin:0; color:#7a5c00; font-size:14px;">
                                                ⏱ Este PIN expira en <strong>15 minutos</strong>. 
                                                Si no lo usas a tiempo, deberás solicitar uno nuevo.
                                            </p>
                                        </td>
                                    </tr>
                                </table>

                                <p style="color:#888888; font-size:13px; line-height:1.6; margin:20px 0 0 0;">
                                    Si no solicitaste la activación de esta cuenta, puedes ignorar este correo. 
                                    Nadie más tiene acceso a tu cuenta.
                                </p>
                            </td>
                        </tr>

                        <!-- FOOTER -->
                        <tr>
                            <td style="background-color:#f9f9f9; border-top:1px solid #eeeeee; padding:20px 40px; text-align:center;">
                                <p style="margin:0; color:#aaaaaa; font-size:12px;">
                                    Este es un correo automático, por favor no respondas a este mensaje.
                                </p>
                                <p style="margin:6px 0 0 0; color:#aaaaaa; font-size:12px;">
                                    © 2025 ASEBEP — Asociación de Becarios
                                </p>
                            </td>
                        </tr>

                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

async def enviar_pin(correo: str, pin: str, db: Session):

    # verificar quota
    hoy = date.today()
    quota = db.query(EmailQuota).filter(EmailQuota.fecha == hoy).first()

    if quota and quota.correos_enviados >= 490:
        raise HTTPException(
            status_code=429,
            detail="Límite diario de correos alcanzado, intenta mañana"
        )

    # armar y enviar correo
    mensaje = MessageSchema(
        subject="Activación de cuenta ASEBEP",
        recipients=[correo],
        body=_html_pin(pin),
        subtype=MessageType.html
    )

    fm = FastMail(mail_config)
    await fm.send_message(mensaje)

    # actualizar contador
    if quota:
        quota.correos_enviados += 1
    else:
        db.add(EmailQuota(fecha=hoy, correos_enviados=1))
    db.commit()

