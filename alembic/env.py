import os
import sys
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from alembic import context

# ---------------------------------------------------------------------
# 1. CONFIGURACIÓN DE RUTAS Y ENTORNO
# ---------------------------------------------------------------------
# Forzamos a que el directorio actual sea parte del PATH de Python.
# Esto evita tener que escribir 'PYTHONPATH=.' en la terminal de Fedora.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cargamos las variables del archivo .env
load_dotenv()

# Este es el objeto de configuración de Alembic, que proporciona
# acceso a los valores dentro del archivo alembic.ini en uso.
config = context.config

# ---------------------------------------------------------------------
# 2. SECCIÓN CRÍTICA: INYECCIÓN DE LA URL DE LA BASE DE DATOS
# ---------------------------------------------------------------------
# Jalamos la URL del .env. Si por algún motivo no la encuentra, 
# dejamos tu URL local de DBeaver como un salvavidas (fallback).
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:password_local@localhost:5432/EL_NOMBRE_DE_TU_DB"
)

# Sobrescribimos la opción 'sqlalchemy.url' del archivo .ini dinámicamente
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Configurar el comportamiento del logging si el archivo ini existe
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------
# 3. CONEXIÓN CON TUS MODELOS DE PYTHON
# ---------------------------------------------------------------------
# Importamos la Base desde tu carpeta 'utils'
from utils.database import Base

# Importamos la carpeta de modelos (esto ejecuta el models/__init__.py)
import models

# Le pasamos los metadatos de tus tablas a Alembic para el --autogenerate
target_metadata = Base.metadata


# ---------------------------------------------------------------------
# 4. FUNCIONES DE EJECUCIÓN DE MIGRACIONES (ESTÁNDAR DE ALEMBIC)
# ---------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Ejecuta las migraciones en modo 'offline'.

    Esto configura el contexto solo con una URL y no con un Engine.
    Al hacerlo, las llamadas a context.execute() emiten el script SQL
    directamente a la salida estándar en lugar de impactar la DB.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta las migraciones en modo 'online'.

    En este escenario, necesitamos crear un Engine asociado con la
    conexión a la base de datos real para inyectar los cambios.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
