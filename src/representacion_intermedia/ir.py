#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/representacion_intermedia/ir.py
------------------------------------------------------------
Representación intermedia (TAC) para Dragon-lang.

Incluye:
- FuncLabel para inicio de funciones
- ParamInstr (paso de cada argumento)
- CallInstr (invocación de función)
- ReturnInstr
- Asignaciones, operaciones binarias/unarias
- Goto, IfGoto, Label
------------------------------------------------------------
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional


# ============================================================
#   Clase base
# ============================================================

class Instruction:
    pass


# ============================================================
#   Control / etiquetas
# ============================================================

@dataclass
class Label(Instruction):
    name: str

    def __str__(self):
        return f"{self.name}:"


@dataclass
class Goto(Instruction):
    target: str

    def __str__(self):
        return f"goto {self.target}"


@dataclass
class IfGoto(Instruction):
    condition: str
    target: str

    def __str__(self):
        return f"if {self.condition} goto {self.target}"


# ============================================================
#   Operaciones básicas
# ============================================================

@dataclass
class Assign(Instruction):
    dest: str
    src: str

    def __str__(self):
        return f"{self.dest} = {self.src}"


@dataclass
class BinaryOp(Instruction):
    dest: str
    op: str
    left: str
    right: str

    def __str__(self):
        return f"{self.dest} = {self.left} {self.op} {self.right}"


@dataclass
class UnaryOp(Instruction):
    dest: str
    op: str
    operand: str

    def __str__(self):
        return f"{self.dest} = {self.op} {self.operand}"


# ============================================================
#   I/O
# ============================================================

@dataclass
class PrintInstr(Instruction):
    value: str

    def __str__(self):
        return f"print {self.value}"


@dataclass
class ReadInstr(Instruction):
    dest: str

    def __str__(self):
        return f"read {self.dest}"


# ============================================================
#   Funciones
# ============================================================

@dataclass
class FuncLabel(Instruction):
    """
    Señala el inicio de una función.
    """
    name: str

    def __str__(self):
        return f"func {self.name}:"


@dataclass
class ParamInstr(Instruction):
    """
    Representa un argumento enviado a una llamada:
       param t3
    """
    value: str

    def __str__(self):
        return f"param {self.value}"


@dataclass
class CallInstr(Instruction):
    """
    Representa la llamada:
       t0 = call fib, 1
    """
    dest: Optional[str]
    callee: str
    arg_count: int

    def __str__(self):
        if self.dest is None:
            return f"call {self.callee}, {self.arg_count}"
        return f"{self.dest} = call {self.callee}, {self.arg_count}"


@dataclass
class ReturnInstr(Instruction):
    value: Optional[str] = None

    def __str__(self):
        if self.value is None:
            return "return"
        return f"return {self.value}"


# ============================================================
#   Programa IR
# ============================================================

@dataclass
class IRProgram:
    instructions: List[Instruction]

    def __str__(self):
        return "\n".join(str(instr) for instr in self.instructions)

    def dump(self):
        return str(self)

