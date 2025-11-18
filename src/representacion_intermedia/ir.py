#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/representacion_intermedia/ir.py
------------------------------------------------------------
Descripción:
Define la representación intermedia (IR) de tipo TAC (Three-Address
Code) para el lenguaje Dragon-Lang.

Este módulo modela instrucciones de bajo nivel independientes de la
máquina física, usadas como puente entre el AST y la máquina virtual.
Incluye:
- Instrucciones de control de flujo y etiquetas.
- Asignaciones y operaciones aritméticas/lógicas.
- Entrada/salida.
- Soporte para funciones: etiquetas de función, paso de parámetros,
  llamadas y retornos.
------------------------------------------------------------
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional


# ============================================================
#   Clase base de instrucciones IR
# ============================================================

class Instruction:
    """
    Clase base abstracta para todas las instrucciones de IR.

    Cada tipo concreto de instrucción (asignación, salto, llamada, etc.)
    hereda de esta clase.
    """
    pass


# ============================================================
#   Control / etiquetas
# ============================================================

@dataclass
class Label(Instruction):
    """
    Etiqueta genérica de salto.

    Se usa como destino de instrucciones Goto/IfGoto.
    """
    name: str

    def __str__(self):
        return f"{self.name}:"


@dataclass
class Goto(Instruction):
    """
    Salto incondicional a una etiqueta.
    """
    target: str

    def __str__(self):
        return f"goto {self.target}"


@dataclass
class IfGoto(Instruction):
    """
    Salto condicional:

        if condition goto target

    Donde 'condition' suele ser una variable/temporal entera
    tratada como booleana (0 = falso, != 0 = verdadero).
    """
    condition: str
    target: str

    def __str__(self):
        return f"if {self.condition} goto {self.target}"


# ============================================================
#   Operaciones básicas
# ============================================================

@dataclass
class Assign(Instruction):
    """
    Asignación simple:

        dest = src
    """
    dest: str
    src: str

    def __str__(self):
        return f"{self.dest} = {self.src}"


@dataclass
class BinaryOp(Instruction):
    """
    Operación binaria:

        dest = left op right

    Donde op puede ser aritmético, lógico o de comparación.
    """
    dest: str
    op: str
    left: str
    right: str

    def __str__(self):
        return f"{self.dest} = {self.left} {self.op} {self.right}"


@dataclass
class UnaryOp(Instruction):
    """
    Operación unaria:

        dest = op operand

    Usada para operadores como '-' y '!'.
    """
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
    """
    Instrucción de salida:

        print value
    """
    value: str

    def __str__(self):
        return f"print {self.value}"


@dataclass
class ReadInstr(Instruction):
    """
    Instrucción de entrada:

        read dest

    Lee desde stdin y almacena en 'dest'.
    """
    dest: str

    def __str__(self):
        return f"read {self.dest}"


# ============================================================
#   Funciones
# ============================================================

@dataclass
class FuncLabel(Instruction):
    """
    Marca el inicio del cuerpo de una función.

    Se utiliza para que la máquina virtual conozca el índice
    de instrucción donde comienza cada función.
    """
    name: str

    def __str__(self):
        return f"func {self.name}:"


@dataclass
class ParamInstr(Instruction):
    """
    Representa el paso de un argumento para una llamada:

        param value

    La máquina virtual apila estos valores antes de procesar
    la instrucción CallInstr.
    """
    value: str

    def __str__(self):
        return f"param {self.value}"


@dataclass
class CallInstr(Instruction):
    """
    Representa una llamada de función:

        dest = call callee, arg_count
        call callee, arg_count        (si dest es None)

    Atributos:
    - dest: temporal/variable donde almacenar el valor de retorno,
            o None si se ignora.
    - callee: nombre de la función.
    - arg_count: número de argumentos previamente pasados con param.
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
    """
    Representa el retorno desde una función:

        return           (sin valor)
        return value     (con valor)

    La máquina virtual se encargará de pasar este valor
    a la función llamadora si corresponde.
    """
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
    """
    Contenedor de la secuencia lineal de instrucciones IR
    que representa todo el programa.
    """
    instructions: List[Instruction]

    def __str__(self):
        return "\n".join(str(instr) for instr in self.instructions)

    def dump(self) -> str:
        """
        Devuelve una representación en texto del programa IR,
        útil para depuración y visualización.
        """
        return str(self)

