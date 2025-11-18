#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/representacion_intermedia/ir_generator.py
------------------------------------------------------------
Descripción:
Generador de Representación Intermedia (IR) en forma de
Three-Address Code (TAC) para Dragon-Lang.

Este módulo toma el AST generado por el parser y produce una
representación lineal de instrucciones de bajo nivel que serán
optimizadas y posteriormente ejecutadas por la máquina virtual.

Responsabilidades:
- Traducir expresiones aritméticas, lógicas y comparaciones.
- Manejar asignaciones, agrupaciones y literales.
- Generar etiquetas para control de flujo.
- Representar bucles y condicionales con saltos TAC.
- Gestionar funciones, parámetros, llamadas y valores de retorno.
- Producir un IR completamente independiente de la estructura del AST.

El resultado es un IRProgram que contiene instrucciones secuenciales
listo para ser optimizado o ejecutado.
------------------------------------------------------------
"""

from __future__ import annotations
from typing import List

from ..analisis_sintactico import ast
from .ir import (
    IRProgram,
    Label,
    Goto,
    IfGoto,
    Assign,
    BinaryOp,
    UnaryOp,
    PrintInstr,
    ReadInstr,
    FuncLabel,
    ParamInstr,
    CallInstr,
    ReturnInstr
)


class IRGenerator:
    """
    Generador de IR (TAC) a partir del AST.

    Este generador asigna temporales, crea etiquetas, y emite la
    secuencia de instrucciones necesarias para representar el flujo
    del programa.
    """

    def __init__(self):
        # Lista final de instrucciones IR
        self.instructions: List = []

        # Contadores para nombres de temporales y etiquetas
        self.temp_count = 0
        self.label_count = 0

    # ============================================================
    # Helpers: creación de temporales y etiquetas
    # ============================================================

    def new_temp(self) -> str:
        """
        Crea un nuevo temporal con nombre único:

            t0, t1, t2, ...

        Se utiliza para almacenar resultados de expresiones.
        """
        t = f"t{self.temp_count}"
        self.temp_count += 1
        return t

    def new_label(self, prefix="L") -> str:
        """
        Crea una nueva etiqueta única con prefijo configurable:

            L0, L1, L2...
            L_then_0, L_else_1, etc.

        Usada para control de flujo.
        """
        l = f"{prefix}{self.label_count}"
        self.label_count += 1
        return l

    def emit(self, instr):
        """
        Agrega una instrucción a la secuencia IR.
        """
        self.instructions.append(instr)

    # ============================================================
    # Entrada principal
    # ============================================================

    def generate(self, program: ast.Program) -> IRProgram:
        """
        Traduce un AST completo a IR.

        Cada función del programa se procesa independientemente.
        """
        self.instructions = []

        for func in program.functions:
            self._gen_function(func)

        return IRProgram(self.instructions)

    # ============================================================
    # Funciones
    # ============================================================

    def _gen_function(self, func: ast.FunctionDecl):
        """
        Genera el bloque IR correspondiente al inicio y cuerpo
        de una función.
        """
        # Emitir etiqueta de inicio
        self.emit(FuncLabel(func.name))

        # Los parámetros ya están declarados por el análisis semántico;
        # no se emite ninguna instrucción aquí.

        # Generar el cuerpo de la función
        self._gen_stmt(func.body)

    # ============================================================
    # Sentencias
    # ============================================================

    def _gen_stmt(self, stmt):
        """
        Traduce cualquier sentencia del AST a instrucciones IR.
        """

        # Importación local para evitar ciclos
        from ..analisis_sintactico import ast

        if isinstance(stmt, ast.BlockStmt):
            for s in stmt.statements:
                self._gen_stmt(s)

        elif isinstance(stmt, ast.VarDeclStmt):
            # Si tiene inicializador, generar:
            #   t0 = <expr>
            #   x = t0
            if stmt.initializer:
                src = self._gen_expr(stmt.initializer)
                self.emit(Assign(stmt.name, src))

        elif isinstance(stmt, ast.ExprStmt):
            # Expresión que se evalúa pero se ignora el resultado
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
            # Leer directamente a la variable
            self.emit(ReadInstr(stmt.target.name))

        elif isinstance(stmt, ast.ReturnStmt):
            if stmt.value:
                val = self._gen_expr(stmt.value)
                self.emit(ReturnInstr(val))
            else:
                self.emit(ReturnInstr())

        else:
            raise RuntimeError(f"Sentencia no soportada: {stmt}")

    # ============================================================
    # IF
    # ============================================================

    def _gen_if(self, stmt: ast.IfStmt):
        """
        Traduce un if / else a TAC utilizando tres etiquetas:
        - then
        - else
        - end
        """
        cond = self._gen_expr(stmt.condition)

        thenL = self.new_label("L_then_")
        elseL = self.new_label("L_else_")
        endL = self.new_label("L_end_")

        # if cond goto L_then_
        self.emit(IfGoto(cond, thenL))
        # goto L_else_
        self.emit(Goto(elseL))

        # L_then_:
        self.emit(Label(thenL))
        self._gen_stmt(stmt.then_branch)
        self.emit(Goto(endL))

        # L_else_:
        self.emit(Label(elseL))
        if stmt.else_branch:
            self._gen_stmt(stmt.else_branch)

        # L_end_:
        self.emit(Label(endL))

    # ============================================================
    # WHILE
    # ============================================================

    def _gen_while(self, stmt: ast.WhileStmt):
        """
        Traducción del ciclo while usando:
        - begin
        - body
        - end
        """
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

    # ============================================================
    # DO-WHILE
    # ============================================================

    def _gen_do_while(self, stmt: ast.DoWhileStmt):
        """
        Traducción del ciclo do-while.
        """
        bodyL = self.new_label("L_do_body_")
        endL = self.new_label("L_do_end_")

        self.emit(Label(bodyL))
        self._gen_stmt(stmt.body)

        cond = self._gen_expr(stmt.condition)
        self.emit(IfGoto(cond, bodyL))

        self.emit(Label(endL))

    # ============================================================
    # FOR
    # ============================================================

    def _gen_for(self, stmt: ast.ForStmt):
        """
        Traducción de un for clásico, con estructura:
            init
            L_begin:
                if cond goto L_body else goto L_end
            L_body:
                body
                update
                goto L_begin
            L_end:
        """
        # init
        if stmt.init:
            self._gen_stmt(stmt.init)

        begin = self.new_label("L_for_begin_")
        body = self.new_label("L_for_body_")
        end = self.new_label("L_for_end_")

        self.emit(Label(begin))

        # condition
        if stmt.condition:
            cond = self._gen_expr(stmt.condition)
            self.emit(IfGoto(cond, body))
            self.emit(Goto(end))
        else:
            # if no condition, always go to body
            self.emit(Goto(body))

        # body
        self.emit(Label(body))
        self._gen_stmt(stmt.body)

        # update
        if stmt.update:
            self._gen_expr(stmt.update)

        self.emit(Goto(begin))
        self.emit(Label(end))

    # ============================================================
    # Expresiones
    # ============================================================

    def _gen_expr(self, expr):
        """
        Traduce una expresión del AST a instrucciones TAC
        y devuelve el nombre del temporal/variable donde queda
        almacenado el resultado.
        """

        from ..analisis_sintactico import ast

        # Literales
        if isinstance(expr, ast.LiteralExpr):
            t = self.new_temp()
            v = expr.value

            if isinstance(v, bool):
                val = "1" if v else "0"
            elif isinstance(v, (int, float)):
                val = str(v)
            elif isinstance(v, str):
                val = '"' + v + '"'
            else:
                raise RuntimeError("Literal no soportado")

            self.emit(Assign(t, val))
            return t

        # Variable
        if isinstance(expr, ast.VarExpr):
            return expr.name

        # Agrupación
        if isinstance(expr, ast.GroupingExpr):
            return self._gen_expr(expr.expr)

        # Unario
        if isinstance(expr, ast.UnaryExpr):
            operand = self._gen_expr(expr.operand)
            t = self.new_temp()
            self.emit(UnaryOp(t, expr.op, operand))
            return t

        # Binario
        if isinstance(expr, ast.BinaryExpr):
            left = self._gen_expr(expr.left)
            right = self._gen_expr(expr.right)
            t = self.new_temp()
            self.emit(BinaryOp(t, expr.op, left, right))
            return t

        # Asignación
        if isinstance(expr, ast.AssignmentExpr):
            val = self._gen_expr(expr.value)
            self.emit(Assign(expr.name, val))
            return expr.name

        # Llamada a función
        if isinstance(expr, ast.CallExpr):
            return self._gen_call(expr)

        raise RuntimeError(f"Expresión no soportada: {expr}")

    # ============================================================
    # Llamada a función
    # ============================================================

    def _gen_call(self, call: ast.CallExpr):
        """
        Traduce una llamada a función:

            param arg1
            param arg2
            t0 = call name, 2
        """
        arg_count = 0

        # Emitir parámetros uno por uno
        for arg in call.args:
            v = self._gen_expr(arg)
            self.emit(ParamInstr(v))
            arg_count += 1

        # Crear temporal destino
        t = self.new_temp()
        self.emit(CallInstr(t, call.callee, arg_count))
        return t


# ============================================================
#   Función global de conveniencia
# ============================================================

def generate_ir(program):
    """
    Genera IR para un AST dado.

    Permite llamar al generador sin instanciar manualmente la clase.
    """
    gen = IRGenerator()
    return gen.generate(program)

