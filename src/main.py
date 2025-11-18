#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/main.py
------------------------------------------------------------
Descripción:
Punto de entrada del compilador/intérprete de Dragon-Lang.

Este módulo orquesta todo el pipeline del compilador:

0) Análisis léxico:    fuente → tokens
1) Análisis sintáctico: tokens → AST
2) Análisis semántico:  AST → verificación de tipos/uso de símbolos
3) Generación de IR:    AST → IR (Three-Address Code)
4) Optimización de IR:  IR → IR optimizado
5) Ejecución:           IR optimizado → Máquina Virtual (VM)

Además:
- Gestiona errores léxicos, sintácticos, semánticos y de la VM.
- Imprime el IR optimizado para fines didácticos y de depuración.
------------------------------------------------------------
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------- FASE 0: Análisis Léxico ----------
from .analisis_lexico.lexer import tokenize, LexicalError

# ---------- FASE 1: Parser ----------
from .analisis_sintactico.parser import parse, ParseError

# ---------- FASE 2: Análisis Semántico ----------
from .analisis_semantico.semantic import SemanticAnalyzer, SemanticError

# ---------- FASE 3: Representación Intermedia ----------
from .representacion_intermedia.ir_generator import generate_ir
from .representacion_intermedia.optimizer import optimize

# ---------- FASE 4: Máquina Virtual ----------
from .codigo_final.vm import run_ir_program, VMError


def main(argv: list[str]) -> int:
    """
    Función principal del compilador/intérprete.

    Parámetros:
    - argv: lista de argumentos de línea de comandos, donde se espera:
        argv[0] = nombre del script
        argv[1] = ruta al archivo fuente .dragon

    Flujo:
    1. Valida argumentos y existencia del archivo.
    2. Lee el código fuente.
    3. Ejecuta las fases del compilador en orden.
    4. Imprime el IR optimizado.
    5. Ejecuta el programa en la máquina virtual.
    6. Maneja y reporta errores de las distintas fases.
    """
    if len(argv) != 2:
        print("Uso: dragonc <archivo.dragon>")
        return 1

    filename = Path(argv[1])
    if not filename.is_file():
        print(f"Error: no se encontró el archivo: {filename}")
        return 1

    # Leer archivo fuente
    source_code = filename.read_text(encoding="utf-8")

    try:
        # --------------------------------------------------------
        # 0) Análisis léxico
        # --------------------------------------------------------
        tokens = list(tokenize(source_code))

        # --------------------------------------------------------
        # 1) Análisis sintáctico → AST
        # --------------------------------------------------------
        program = parse(tokens, source_code)

        # --------------------------------------------------------
        # 2) Análisis semántico
        # --------------------------------------------------------
        analyzer = SemanticAnalyzer()
        analyzer.analyze(program)

        # --------------------------------------------------------
        # 3) Generación de IR (TAC)
        # --------------------------------------------------------
        ir = generate_ir(program)

        # --------------------------------------------------------
        # 4) Optimización de IR
        # --------------------------------------------------------
        optimized_ir = optimize(ir)

        print("=== IR optimizado (TAC) ===")
        print(optimized_ir.dump())
        print("\n=== Ejecución en Máquina Virtual ===")

        # --------------------------------------------------------
        # Construir mapa: nombre_función → [param1, param2, ...]
        # (Necesario para que la VM asigne argumentos a parámetros)
        # --------------------------------------------------------
        func_param_names = {
            f.name: [p.name for p in f.params]
            for f in program.functions
        }

        # --------------------------------------------------------
        # 5) Ejecución en máquina virtual
        # --------------------------------------------------------
        ret = run_ir_program(optimized_ir, func_param_names)

        if ret is not None:
            print(f"\nPrograma finalizó con código de retorno: {ret}")

    # ------------------------------------------------------------
    # Manejo de errores por fase
    # ------------------------------------------------------------
    except LexicalError as e:
        print(e)
        return 1
    except ParseError as e:
        print(e)
        return 1
    except SemanticError as e:
        print(f"Error semántico: {e}")
        return 1
    except VMError as e:
        print(f"Error en máquina virtual: {e}")
        return 1
    except Exception as e:
        # Captura de seguridad para errores no previstos
        print(f"Error inesperado: {e}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

