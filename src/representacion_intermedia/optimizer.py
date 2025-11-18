#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/representacion_intermedia/optimizer.py
------------------------------------------------------------
Descripción:
Implementa optimizaciones básicas para la representación
intermedia (IR) de Dragon-Lang.

Su propósito es mejorar el código TAC eliminando redundancias y
simplificando operaciones antes de la ejecución en la máquina virtual.

Incluye:
1) Propagación de constantes
   Reemplaza variables temporales cuyo valor es constante por el literal
   correspondiente en el resto del código.

2) Constant folding
   Evalúa en tiempo de compilación operaciones binarias/unarias cuyos
   operandos son constantes (int, float, bool, string).

3) Eliminación de temporales muertos
   Elimina asignaciones a temporales que nunca se usan posteriormente
   (dead-code elimination básica).

4) Eliminación de gotos triviales
   Remueve saltos que apuntan inmediatamente a la siguiente instrucción
   con una etiqueta.

El optimizador produce un nuevo IRProgram equivalente pero más eficiente.
------------------------------------------------------------
"""

from __future__ import annotations
from typing import List, Dict, Set, Optional, Union

from .ir import (
    IRProgram,
    Instruction,
    Assign,
    BinaryOp,
    UnaryOp,
    PrintInstr,
    ReadInstr,
    Goto,
    IfGoto,
    Label,
    ReturnInstr,
    ParamInstr,
    CallInstr,
    FuncLabel
)


# ============================================================
#   Optimizador principal
# ============================================================

class Optimizer:
    """
    Clase encargada de aplicar las distintas etapas de optimización,
    produciendo un IR simplificado y más eficiente.
    """

    def optimize(self, ir: IRProgram) -> IRProgram:
        """
        Aplica en orden:
        1. Propagación de constantes
        2. Eliminación de temporales muertos
        3. Eliminación de gotos triviales
        """
        instrs = ir.instructions
        instrs = self.constant_propagation(instrs)
        instrs = self.remove_dead_temps(instrs)
        instrs = self.remove_trivial_gotos(instrs)
        return IRProgram(instrs)

    # ============================================================
    # 1) Propagación de constantes
    # ============================================================

    def constant_propagation(self, instrs: List[Instruction]) -> List[Instruction]:
        """
        Recorre las instrucciones buscando asignaciones constantes del tipo:
            t0 = 5
            t1 = "hola"

        Estas constantes se almacenan en un diccionario y se sustituyen
        posteriormente donde aparezcan.
        """
        consts: Dict[str, str] = {}
        new = []

        for instr in instrs:

            # Asignaciones constantes directas
            if isinstance(instr, Assign) and self._is_constant(instr.src):
                consts[instr.dest] = instr.src
                new.append(instr)
                continue

            # Operaciones binarias
            if isinstance(instr, BinaryOp):
                left = consts.get(instr.left, instr.left)
                right = consts.get(instr.right, instr.right)

                # Constant folding
                if self._is_constant(left) and self._is_constant(right):
                    folded = self._fold_binary(instr.op, left, right)
                    new.append(Assign(instr.dest, folded))
                    consts[instr.dest] = folded
                else:
                    new.append(BinaryOp(instr.dest, instr.op, left, right))
                continue

            # Operaciones unarias
            if isinstance(instr, UnaryOp):
                operand = consts.get(instr.operand, instr.operand)

                if self._is_constant(operand):
                    folded = self._fold_unary(instr.op, operand)
                    new.append(Assign(instr.dest, folded))
                    consts[instr.dest] = folded
                else:
                    new.append(UnaryOp(instr.dest, instr.op, operand))
                continue

            # Otras instrucciones no se optimizan aquí
            new.append(instr)

        return new

    # ============================================================
    # Constant folding (binario)
    # ============================================================

    def _fold_binary(self, op: str, left: str, right: str) -> str:
        """
        Realiza la evaluación de una operación binaria si ambos operandos
        son constantes. Soporta strings en operaciones de concatenación.
        """
        # Strings
        if left.startswith('"') or right.startswith('"'):
            if op == "+":
                # Concatenar quitando comillas duplicadas
                return f"{left[:-1]}{right[1:]}"
            raise RuntimeError(f"No se puede aplicar '{op}' sobre cadenas.")

        # Convertir a número
        a = float(left) if "." in left else int(left)
        b = float(right) if "." in right else int(right)

        # Resolver operador
        if op == "+": r = a + b
        elif op == "-": r = a - b
        elif op == "*": r = a * b
        elif op == "/": r = a / b
        elif op == "%":
            if isinstance(a, float) or isinstance(b, float):
                raise RuntimeError("El operador % solo acepta enteros.")
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

        return repr(r).replace("'", "")

    # ============================================================
    # Constant folding (unario)
    # ============================================================

    def _fold_unary(self, op: str, operand: str) -> str:
        """
        Evalúa operaciones unarias sobre constantes:
        - -x
        - !x
        """
        if operand.startswith('"'):
            raise RuntimeError("No se pueden aplicar unarios a cadenas.")

        val = float(operand) if "." in operand else int(operand)

        if op == "-":
            return str(-val)
        elif op == "!":
            return "1" if not bool(val) else "0"

        raise RuntimeError(f"Operador unario no soportado: {op}")

    # ============================================================
    # Verificador de literales constantes
    # ============================================================

    def _is_constant(self, val: str) -> bool:
        """
        Determina si un valor es un literal constante en IR:
        - Strings entre comillas
        - Números enteros o reales
        - Booleanos codificados como 0 o 1
        """
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
        """
        Detecta temporales asignados pero nunca usados posteriormente
        y elimina las instrucciones correspondientes.
        """
        used: Set[str] = set()

        # Fase 1: detectar valores usados
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

            elif isinstance(instr, IfGoto):
                used.add(instr.condition)

            elif isinstance(instr, ReturnInstr) and instr.value:
                used.add(instr.value)

            elif isinstance(instr, ParamInstr):
                used.add(instr.value)

            elif isinstance(instr, CallInstr):
                if instr.dest:
                    used.add(instr.dest)

        # Fase 2: reconstruir eliminando instrucciones innecesarias
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
        """
        Elimina instrucciones:
            goto L1
        cuando L1 es la instrucción inmediata siguiente.
        """
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
    """
    Ejecuta el optimizador sobre un IRProgram dado.
    """
    return Optimizer().optimize(ir)

