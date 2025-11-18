#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/representacion_intermedia/optimizer.py
------------------------------------------------------------
Optimizador para Dragon-lang:

- Propagación de constantes
- Constant folding (int, float, bool)
- Eliminación de temporales muertos
- Eliminación de gotos triviales
- Compatible con:
    - ParamInstr
    - CallInstr
    - FuncLabel
    - Literales string
------------------------------------------------------------
"""

from __future__ import annotations
from typing import List, Dict, Set, Optional, Union

from .ir import (
    IRProgram,
    Instruction,
    Assign, BinaryOp, UnaryOp,
    PrintInstr, ReadInstr,
    Goto, IfGoto, Label,
    ReturnInstr,
    ParamInstr, CallInstr, FuncLabel
)


# ============================================================
#   Optimizador principal
# ============================================================

class Optimizer:

    def optimize(self, ir: IRProgram) -> IRProgram:
        instrs = ir.instructions
        instrs = self.constant_propagation(instrs)
        instrs = self.remove_dead_temps(instrs)
        instrs = self.remove_trivial_gotos(instrs)
        return IRProgram(instrs)

    # ============================================================
    # 1) PROPAGACIÓN DE CONSTANTES
    # ============================================================

    def constant_propagation(self, instrs: List[Instruction]) -> List[Instruction]:
        consts: Dict[str, str] = {}
        new = []

        for instr in instrs:

            # ------------------------
            # Asignaciones de tipo:
            #    t0 = 5
            #    t1 = 3.14
            #    t2 = "hola"
            # ------------------------
            if isinstance(instr, Assign) and self._is_constant(instr.src):
                consts[instr.dest] = instr.src
                new.append(instr)
                continue

            # ------------------------
            # Operaciones binarias
            # ------------------------
            if isinstance(instr, BinaryOp):
                left = consts.get(instr.left, instr.left)
                right = consts.get(instr.right, instr.right)

                if self._is_constant(left) and self._is_constant(right):
                    folded = self._fold_binary(instr.op, left, right)
                    new.append(Assign(instr.dest, folded))
                    consts[instr.dest] = folded
                else:
                    new.append(BinaryOp(instr.dest, instr.op, left, right))
                continue

            # ------------------------
            # Operaciones unarias
            # ------------------------
            if isinstance(instr, UnaryOp):
                operand = consts.get(instr.operand, instr.operand)

                if self._is_constant(operand):
                    folded = self._fold_unary(instr.op, operand)
                    new.append(Assign(instr.dest, folded))
                    consts[instr.dest] = folded
                else:
                    new.append(UnaryOp(instr.dest, instr.op, operand))
                continue

            # ------------------------
            # Instrucciones que NO se optimizan
            # param, call, print, read, labels...
            # ------------------------
            new.append(instr)

        return new

    # ============================================================
    # CONSTANT FOLDING (binario)
    # ============================================================

    def _fold_binary(self, op: str, left: str, right: str) -> str:
        # Si es string → solo permitimos "+"
        if left.startswith('"') or right.startswith('"'):
            if op == "+":
                return f"{left[:-1]}{right[1:]}"  # concatenar strings
            raise RuntimeError(f"No se puede aplicar '{op}' sobre strings")

        # convertir a número
        a = float(left) if "." in left else int(left)
        b = float(right) if "." in right else int(right)

        # operaciones
        if op == "+": r = a + b
        elif op == "-": r = a - b
        elif op == "*": r = a * b
        elif op == "/": r = a / b
        elif op == "%":
            if isinstance(a, float) or isinstance(b, float):
                raise RuntimeError("El operador % solo acepta enteros")
            r = a % b
        elif op == "<": r = int(a < b)
        elif op == "<=": r = int(a <= b)
        elif op == ">": r = int(a > b)
        elif op == ">=": r = int(a >= b)
        elif op == "==": r = int(a == b)
        elif op == "!=": r = int(a != b)
        elif op == "&&": r = int(bool(a) and bool(b))
        elif op == "||": r = int(bool(a) or bool(b))
        else:
            raise RuntimeError(f"Operador no soportado en folding: {op}")

        # devolver formato literal correcto
        return repr(r).replace("'", "")

    # ============================================================
    # CONSTANT FOLDING (unario)
    # ============================================================

    def _fold_unary(self, op: str, operand: str) -> str:
        if operand.startswith('"'):
            raise RuntimeError("No se pueden aplicar unarios a cadenas")

        val = float(operand) if "." in operand else int(operand)

        if op == "-":
            return str(-val)
        elif op == "!":
            return "1" if not bool(val) else "0"

        raise RuntimeError(f"Operador unario no soportado: {op}")

    # ============================================================
    # Verificador de literal constante
    # ============================================================

    def _is_constant(self, val: str) -> bool:
        if val.startswith('"') and val.endswith('"'):
            return True
        if val.replace('.', '', 1).isdigit():
            return True
        if val in ("0", "1"):
            return True
        return False

    # ============================================================
    # 2) Eliminación de temporales muertos
    # ============================================================

    def remove_dead_temps(self, instrs: List[Instruction]) -> List[Instruction]:
        used: Set[str] = set()

        # Colectar variables usadas
        for instr in instrs:

            if isinstance(instr, Assign):
                used.add(instr.src)

            elif isinstance(instr, BinaryOp):
                used.add(instr.left)
                used.add(instr.right)

            elif isinstance(instr, UnaryOp):
                used.add(instr.operand)

            elif isinstance(instr, PrintInstr):
                used.add(instr.value)

            elif isinstance(instr, ReadInstr):
                pass  # destino, no fuente

            elif isinstance(instr, IfGoto):
                used.add(instr.condition)

            elif isinstance(instr, ReturnInstr) and instr.value:
                used.add(instr.value)

            elif isinstance(instr, ParamInstr):
                used.add(instr.value)

            elif isinstance(instr, CallInstr):
                # destino puede ser None, pero si existe siempre se considera utilizado
                if instr.dest:
                    used.add(instr.dest)

        # reconstruir omitiendo temporales muertos
        new = []
        for instr in instrs:
            if isinstance(instr, Assign):
                if instr.dest.startswith("t") and instr.dest not in used:
                    continue
            new.append(instr)

        return new

    # ============================================================
    # 3) Eliminación de gotos triviales
    # ============================================================

    def remove_trivial_gotos(self, instrs: List[Instruction]) -> List[Instruction]:
        new = []
        for i, instr in enumerate(instrs):
            if isinstance(instr, Goto):
                if i + 1 < len(instrs) and isinstance(instrs[i + 1], Label):
                    if instr.target == instrs[i + 1].name:
                        continue
            new.append(instr)
        return new


# ============================================================
#   Función global
# ============================================================

def optimize(ir: IRProgram):
    return Optimizer().optimize(ir)

