#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/representacion_intermedia/ir_generator.py
------------------------------------------------------------
Generación de TAC (IR) para Dragon-lang con soporte pleno de:
- Funciones con parámetros
- Llamadas a funciones (call)
- Paso de argumentos (param)
- Literales (int, float, bool, string)
- Strings con concatenación
- Operadores aritméticos, lógicos, comparaciones
- return con o sin valor
------------------------------------------------------------
"""

from __future__ import annotations
from typing import List

from ..analisis_sintactico import ast
from .ir import (
    IRProgram,
    Label, Goto, IfGoto,
    Assign, BinaryOp, UnaryOp,
    PrintInstr, ReadInstr,
    FuncLabel, ParamInstr, CallInstr,
    ReturnInstr
)


class IRGenerator:
    def __init__(self):
        self.instructions: List = []
        self.temp_count = 0
        self.label_count = 0

    # --------------------------------------------------------
    # Helpers: temporales y etiquetas
    # --------------------------------------------------------

    def new_temp(self) -> str:
        t = f"t{self.temp_count}"
        self.temp_count += 1
        return t

    def new_label(self, prefix="L") -> str:
        l = f"{prefix}{self.label_count}"
        self.label_count += 1
        return l

    def emit(self, instr):
        self.instructions.append(instr)

    # --------------------------------------------------------
    # Entrada principal
    # --------------------------------------------------------

    def generate(self, program: ast.Program) -> IRProgram:
        self.instructions = []

        for func in program.functions:
            self._gen_function(func)

        return IRProgram(self.instructions)

    # --------------------------------------------------------
    # Funciones
    # --------------------------------------------------------

    def _gen_function(self, func: ast.FunctionDecl):
        # Etiqueta de inicio
        self.emit(FuncLabel(func.name))

        # Los parámetros ya son variables locales (semantic los declara)
        # No necesitamos generar nada aquí.

        # Generar cuerpo
        self._gen_stmt(func.body)

    # --------------------------------------------------------
    # Sentencias
    # --------------------------------------------------------

    def _gen_stmt(self, stmt):
        from ..analisis_sintactico import ast

        if isinstance(stmt, ast.BlockStmt):
            for s in stmt.statements:
                self._gen_stmt(s)

        elif isinstance(stmt, ast.VarDeclStmt):
            if stmt.initializer:
                src = self._gen_expr(stmt.initializer)
                self.emit(Assign(stmt.name, src))

        elif isinstance(stmt, ast.ExprStmt):
            self._gen_expr(stmt.expr)

        elif isinstance(stmt, ast.IfStmt):
            self._gen_if(stmt)

        elif isinstance(stmt, ast.WhileStmt):
            self._gen_while(stmt)

        elif isinstance(stmt, ast.DoWhileStmt):
            self._gen_do_while(stmt)

        elif isinstance(stmt, ast.ForStmt):
            self._gen_for(stmt)

        elif isinstance(stmt, ast.PrintStmt):
            val = self._gen_expr(stmt.expr)
            self.emit(PrintInstr(val))

        elif isinstance(stmt, ast.ReadStmt):
            self.emit(ReadInstr(stmt.target.name))

        elif isinstance(stmt, ast.ReturnStmt):
            if stmt.value:
                val = self._gen_expr(stmt.value)
                self.emit(ReturnInstr(val))
            else:
                self.emit(ReturnInstr())

        else:
            raise RuntimeError(f"stmt no soportado: {stmt}")

    # --------------------------------------------------------
    # IF
    # --------------------------------------------------------

    def _gen_if(self, stmt: ast.IfStmt):
        cond = self._gen_expr(stmt.condition)

        thenL = self.new_label("L_then_")
        elseL = self.new_label("L_else_")
        endL = self.new_label("L_end_")

        self.emit(IfGoto(cond, thenL))
        self.emit(Goto(elseL))

        self.emit(Label(thenL))
        self._gen_stmt(stmt.then_branch)
        self.emit(Goto(endL))

        self.emit(Label(elseL))
        if stmt.else_branch:
            self._gen_stmt(stmt.else_branch)

        self.emit(Label(endL))

    # --------------------------------------------------------
    # WHILE
    # --------------------------------------------------------

    def _gen_while(self, stmt: ast.WhileStmt):
        begin = self.new_label("L_while_begin_")
        body = self.new_label("L_while_body_")
        end = self.new_label("L_while_end_")

        self.emit(Label(begin))

        cond = self._gen_expr(stmt.condition)
        self.emit(IfGoto(cond, body))
        self.emit(Goto(end))

        self.emit(Label(body))
        self._gen_stmt(stmt.body)
        self.emit(Goto(begin))

        self.emit(Label(end))

    # --------------------------------------------------------
    # DO-WHILE
    # --------------------------------------------------------

    def _gen_do_while(self, stmt: ast.DoWhileStmt):
        bodyL = self.new_label("L_do_body_")
        endL = self.new_label("L_do_end_")

        self.emit(Label(bodyL))
        self._gen_stmt(stmt.body)

        cond = self._gen_expr(stmt.condition)
        self.emit(IfGoto(cond, bodyL))

        self.emit(Label(endL))

    # --------------------------------------------------------
    # FOR
    # --------------------------------------------------------

    def _gen_for(self, stmt: ast.ForStmt):
        if stmt.init:
            self._gen_stmt(stmt.init)

        begin = self.new_label("L_for_begin_")
        body = self.new_label("L_for_body_")
        end = self.new_label("L_for_end_")

        self.emit(Label(begin))

        if stmt.condition:
            cond = self._gen_expr(stmt.condition)
            self.emit(IfGoto(cond, body))
            self.emit(Goto(end))
        else:
            self.emit(Goto(body))

        self.emit(Label(body))
        self._gen_stmt(stmt.body)

        if stmt.update:
            self._gen_expr(stmt.update)

        self.emit(Goto(begin))
        self.emit(Label(end))

    # --------------------------------------------------------
    # Expresiones
    # --------------------------------------------------------

    def _gen_expr(self, expr):
        from ..analisis_sintactico import ast

        # --------------------------------------------
        # Literales
        # --------------------------------------------
        if isinstance(expr, ast.LiteralExpr):
            t = self.new_temp()

            v = expr.value
            if isinstance(v, bool):
                val = "1" if v else "0"
            elif isinstance(v, (int, float)):
                val = str(v)
            elif isinstance(v, str):
                # envolver string en comillas
                val = '"' + v + '"'
            else:
                raise RuntimeError("literal no soportado")

            self.emit(Assign(t, val))
            return t

        # --------------------------------------------
        # Variable
        # --------------------------------------------
        if isinstance(expr, ast.VarExpr):
            return expr.name

        # --------------------------------------------
        # Agrupación
        # --------------------------------------------
        if isinstance(expr, ast.GroupingExpr):
            return self._gen_expr(expr.expr)

        # --------------------------------------------
        # Unario
        # --------------------------------------------
        if isinstance(expr, ast.UnaryExpr):
            operand = self._gen_expr(expr.operand)
            t = self.new_temp()
            self.emit(UnaryOp(t, expr.op, operand))
            return t

        # --------------------------------------------
        # Binario (incluye concatenación)
        # --------------------------------------------
        if isinstance(expr, ast.BinaryExpr):
            left = self._gen_expr(expr.left)
            right = self._gen_expr(expr.right)

            t = self.new_temp()
            self.emit(BinaryOp(t, expr.op, left, right))
            return t

        # --------------------------------------------
        # Asignación
        # --------------------------------------------
        if isinstance(expr, ast.AssignmentExpr):
            val = self._gen_expr(expr.value)
            self.emit(Assign(expr.name, val))
            return expr.name

        # --------------------------------------------
        # Llamada a función
        # --------------------------------------------
        if isinstance(expr, ast.CallExpr):
            return self._gen_call(expr)

        raise RuntimeError(f"Expresión no soportada: {expr}")

    # --------------------------------------------------------
    # Llamada a función
    # --------------------------------------------------------

    def _gen_call(self, call: ast.CallExpr):
        # Primero emitir los parámetros
        arg_count = 0
        for arg in call.args:
            v = self._gen_expr(arg)
            self.emit(ParamInstr(v))
            arg_count += 1

        # Si esperamos valor de retorno, crear temporal
        t = self.new_temp()
        self.emit(CallInstr(t, call.callee, arg_count))
        return t


# ============================================================
# Función global
# ============================================================

def generate_ir(program):
    gen = IRGenerator()
    return gen.generate(program)

