#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/main.py
------------------------------------------------------------
Punto de entrada del compilador Dragon-lang.

Fases:
0) Análisis léxico
1) Parser → AST
2) Análisis semántico
3) Generación de IR (TAC)
4) Optimización del IR
5) Ejecución en máquina virtual (con pila de llamadas)
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
        # 0) Tokenizar
        tokens = list(tokenize(source_code))

        # 1) Parsear
        program = parse(tokens, source_code)

        # 2) Análisis semántico
        analyzer = SemanticAnalyzer()
        analyzer.analyze(program)

        # 3) Generación de IR
        ir = generate_ir(program)

        # 4) Optimización
        optimized_ir = optimize(ir)

        print("=== IR optimizado (TAC) ===")
        print(optimized_ir.dump())
        print("\n=== Ejecución en Máquina Virtual ===")

        # Construir mapa: nombre_función → [param1, param2, ...]
        func_param_names = {
            f.name: [p.name for p in f.params]
            for f in program.functions
        }

        # 5) Ejecutar
        ret = run_ir_program(optimized_ir, func_param_names)

        if ret is not None:
            print(f"\nPrograma finalizó con código de retorno: {ret}")

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
        print(f"Error inesperado: {e}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

