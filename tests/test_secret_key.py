"""
Pruebas de la validación de SECRET_KEY al importar `core.security`.

Una clave vacía o con espacios en los extremos produce firmas distintas entre
procesos: el login emite un token y la verificación lo rechaza con
"Signature verification failed". El módulo debe fallar al arrancar en lugar
de permitir ese estado.
"""

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _importar_security(entorno: dict) -> subprocess.CompletedProcess:
    """Importa core.security en un proceso limpio con el entorno indicado."""
    return subprocess.run(
        [sys.executable, "-c", "import core.security"],
        cwd=RAIZ,
        env=entorno,
        capture_output=True,
        text=True,
    )


def _entorno(**cambios):
    import os

    base = dict(os.environ)
    # .env del proyecto no debe influir en el caso probado.
    base["PYTHONPATH"] = str(RAIZ)
    for clave, valor in cambios.items():
        base[clave] = valor
    return base


def test_secret_key_vacia_impide_arrancar():
    resultado = _importar_security(_entorno(SECRET_KEY=""))

    assert resultado.returncode != 0
    assert "SECRET_KEY" in resultado.stderr


def test_secret_key_con_espacio_inicial_impide_arrancar():
    resultado = _importar_security(_entorno(SECRET_KEY=" clave-de-pruebas"))

    assert resultado.returncode != 0
    assert "espacios" in resultado.stderr


def test_secret_key_con_espacio_final_impide_arrancar():
    resultado = _importar_security(_entorno(SECRET_KEY="clave-de-pruebas "))

    assert resultado.returncode != 0
    assert "espacios" in resultado.stderr


def test_secret_key_valida_permite_arrancar():
    resultado = _importar_security(_entorno(SECRET_KEY="clave-de-pruebas"))

    assert resultado.returncode == 0, resultado.stderr
