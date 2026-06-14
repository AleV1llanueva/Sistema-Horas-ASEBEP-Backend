import os 
from dotenv import load_dotenv
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

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

async def enviar_pin(correo: str, pin: str):
    mensaje = MessageSchema(
        subject="Activación de cuenta ASEBEP",
        recipients=[correo],
        body=f"""
        Hola, 

        Tu PIN de activación es: {pin}

        Este PIN expira en 15 minutos.
        
        Si no solicitaste esto, ignora este correo.
        """,

        subtype=MessageType.plain
    )

    fm = FastMail(mail_config)
    await fm.send_message(mensaje)
