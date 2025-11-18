#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/analisis_semantico/semantic.py
------------------------------------------------------------
Análisis semántico para Dragon-lang.

Soporta:
- funciones con parámetros
- llamadas a funciones
- int, float, bool, string
- coerción automática int→float
- concatenación string
- return con tipo inferido
- scopes anidados
------------------------------------------------------------
"""

from __future__ import annotations
from typing import Optional, List

from .symbol_table import SymbolTable, SymbolTableError
from ..analisis_sintactico import ast


# ============================================================
#   Errores semánticos
# ============================================================

class SemanticError(Exception):
    pass


# ============================================================
#   Analizador semántico
# ============================================================

class SemanticAnalyzer:
    def __init__(self) -> None:
        self.symtab = SymbolTable()
        self.current_function: Optional[str] = None
        self.current_return_type: Optional[str] = None

    # --------------------------------------------------------
    # Entrada principal
    # --------------------------------------------------------

    def analyze(self, program: ast.Program) -> None:
        # Registrar funciones en alcance global
        for func in program.functions:
            try:
                self.symtab.define_func(func.name, return_type=None)
            except SymbolTableError as e:
                raise SemanticError(f"Función redeclarada: {func.name}. Detalle: {e}")

        # Analizar cada función
        for func in program.functions:
            self._analyze_function(func)

    # --------------------------------------------------------
    # Funciones y parámetros
    # --------------------------------------------------------

    def _analyze_function(self, func: ast.FunctionDecl) -> None:
        # Entrar al scope de la función
        self.symtab.push_scope(func.name)
        self.current_function = func.name
        self.current_return_type = None

        # Definir parámetros
        for p in func.params:
            try:
                self.symtab.define_var(p.name, p.param_type)
            except SymbolTableError:
                raise SemanticError(f"Parámetro redeclarado: {p.name}")

        # Analizar cuerpo
        self._analyze_stmt(func.body)

        # Salir del scope
        self.symtab.pop_scope()

        self.current_function = None
        self.current_return_type = None

    # --------------------------------------------------------
    # Sentencias
    # --------------------------------------------------------

    def _analyze_stmt(self, stmt: ast.Stmt) -> None:
        if isinstance(stmt, ast.BlockStmt):
            self.symtab.push_scope("block")
            for s in stmt.statements:
                self._analyze_stmt(s)
            self.symtab.pop_scope()

        elif isinstance(stmt, ast.VarDeclStmt):
            self._declare_var(stmt)

        elif isinstance(stmt, ast.ExprStmt):
            self._analyze_expr(stmt.expr)

        elif isinstance(stmt, ast.IfStmt):
            self._analyze_if(stmt)

        elif isinstance(stmt, ast.WhileStmt):
            self._analyze_while(stmt)

        elif isinstance(stmt, ast.DoWhileStmt):
            self._analyze_do_while(stmt)

        elif isinstance(stmt, ast.ForStmt):
            self._analyze_for(stmt)

        elif isinstance(stmt, ast.PrintStmt):
            self._analyze_expr(stmt.expr)

        elif isinstance(stmt, ast.ReadStmt):
            self._analyze_read(stmt)

        elif isinstance(stmt, ast.ReturnStmt):
            self._analyze_return(stmt)

        else:
            raise SemanticError(f"Sentencia no soportada: {type(stmt).__name__}")

    # --------------------------------------------------------
    # Declaraciones
    # --------------------------------------------------------

    def _declare_var(self, stmt: ast.VarDeclStmt):
        try:
            self.symtab.define_var(stmt.name, stmt.var_type)
        except SymbolTableError as e:
            raise SemanticError(str(e))

        if stmt.initializer:
            init_type = self._analyze_expr(stmt.initializer)
            self._ensure_type_compatible(stmt.var_type, init_type,
                                         f"Inicialización inválida de '{stmt.name}'")

    # --------------------------------------------------------
    # Control de flujo
    # --------------------------------------------------------

    def _analyze_if(self, stmt: ast.IfStmt):
        cond_type = self._analyze_expr(stmt.condition)
        self._require_type(cond_type, "bool", "La condición de if debe ser bool")

        self._analyze_stmt(stmt.then_branch)
        if stmt.else_branch:
            self._analyze_stmt(stmt.else_branch)

    def _analyze_while(self, stmt: ast.WhileStmt):
        cond_type = self._analyze_expr(stmt.condition)
        self._require_type(cond_type, "bool", "La condición de while debe ser bool")
        self._analyze_stmt(stmt.body)

    def _analyze_do_while(self, stmt: ast.DoWhileStmt):
        self._analyze_stmt(stmt.body)
        cond_type = self._analyze_expr(stmt.condition)
        self._require_type(cond_type, "bool", "La condición de do-while debe ser bool")

    def _analyze_for(self, stmt: ast.ForStmt):
        self.symtab.push_scope("for")

        if stmt.init:
            self._analyze_stmt(stmt.init)

        if stmt.condition:
            cond_type = self._analyze_expr(stmt.condition)
            self._require_type(cond_type, "bool", "La condición de for debe ser bool")

        if stmt.update:
            self._analyze_expr(stmt.update)

        self._analyze_stmt(stmt.body)

        self.symtab.pop_scope()

    # --------------------------------------------------------
    # return
    # --------------------------------------------------------

    def _analyze_return(self, stmt: ast.ReturnStmt):
        if stmt.value is None:
            # return;  → tipo void
            ret_type = "void"
        else:
            ret_type = self._analyze_expr(stmt.value)

        if self.current_return_type is None:
            # primera aparición define el tipo de retorno
            self.current_return_type = ret_type
            # actualizar en tabla de funciones
            self.symtab.set_func_return_type(self.current_function, ret_type)
        else:
            if self.current_return_type != ret_type:
                raise SemanticError(
                    f"Tipos de retorno inconsistentes en función '{self.current_function}'. "
                    f"Esperado '{self.current_return_type}', obtenido '{ret_type}'"
                )

    # --------------------------------------------------------
    # read
    # --------------------------------------------------------

    def _analyze_read(self, stmt: ast.ReadStmt):
        symbol = self.symtab.resolve(stmt.target.name)
        if symbol is None or symbol.kind != "var":
            raise SemanticError(f"Variable no declarada usada en read: '{stmt.target.name}'")

    # --------------------------------------------------------
    # Expresiones
    # --------------------------------------------------------

    def _analyze_expr(self, expr: ast.Expr) -> str:
        if isinstance(expr, ast.LiteralExpr):
            return self._infer_literal_type(expr.value)

        if isinstance(expr, ast.VarExpr):
            return self._lookup_var(expr.name)

        if isinstance(expr, ast.UnaryExpr):
            return self._analyze_unary(expr)

        if isinstance(expr, ast.BinaryExpr):
            return self._analyze_binary(expr)

        if isinstance(expr, ast.GroupingExpr):
            return self._analyze_expr(expr.expr)

        if isinstance(expr, ast.AssignmentExpr):
            return self._analyze_assignment(expr)

        if isinstance(expr, ast.CallExpr):
            return self._analyze_call(expr)

        raise SemanticError(f"Expresión no soportada: {type(expr).__name__}")

    # --------------------------------------------------------
    # literales
    # --------------------------------------------------------

    def _infer_literal_type(self, value):
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "int"
        if isinstance(value, float):
            return "float"
        if isinstance(value, str):
            return "string"
        raise SemanticError("Literal no soportado")

    # --------------------------------------------------------
    # lookup de variable
    # --------------------------------------------------------

    def _lookup_var(self, name: str):
        symbol = self.symtab.resolve(name)
        if symbol is None:
            raise SemanticError(f"Variable no declarada: '{name}'")
        return symbol.type

    # --------------------------------------------------------
    # unarias
    # --------------------------------------------------------

    def _analyze_unary(self, expr: ast.UnaryExpr) -> str:
        operand_type = self._analyze_expr(expr.operand)

        if expr.op == "-":
            self._require_numeric(operand_type,
                                  "El operador '-' requiere int o float")
            return operand_type

        if expr.op == "!":
            self._require_type(operand_type, "bool",
                               "El operador '!' requiere bool")
            return "bool"

        raise SemanticError(f"Operador unario no soportado: {expr.op}")

    # --------------------------------------------------------
    # binarias
    # --------------------------------------------------------

    def _analyze_binary(self, expr: ast.BinaryExpr) -> str:
        left = self._analyze_expr(expr.left)
        right = self._analyze_expr(expr.right)
        op = expr.op

        # concatenación string
        if op == "+" and (left == "string" or right == "string"):
            return "string"

        # comparaciones → requieren tipos compatibles
        if op in ("<", "<=", ">", ">=", "==", "!="):
            self._ensure_type_compatible(left, right,
                                         "Comparación entre tipos incompatibles")
            return "bool"

        # lógicos
        if op in ("&&", "||"):
            self._require_type(left, "bool",
                               "Operador lógico requiere bool")
            self._require_type(right, "bool",
                               "Operador lógico requiere bool")
            return "bool"

        # aritméticos
        if op in ("+", "-", "*", "/", "%"):
            self._require_numeric(left, "Operador aritmético inválido")
            self._require_numeric(right, "Operador aritmético inválido")

            # % solo para int
            if op == "%" and (left != "int" or right != "int"):
                raise SemanticError("El operador % requiere operandos int")

            # mezcla int+float → float
            if left == "float" or right == "float":
                return "float"

            return "int"

        raise SemanticError(f"Operador binario no soportado: {op}")

    # --------------------------------------------------------
    # asignación
    # --------------------------------------------------------

    def _analyze_assignment(self, expr: ast.AssignmentExpr) -> str:
        symbol = self.symtab.resolve(expr.name)
        if symbol is None:
            raise SemanticError(f"Variable no declarada: '{expr.name}'")

        val_type = self._analyze_expr(expr.value)
        self._ensure_type_compatible(symbol.type, val_type,
                                     f"Asignación inválida a '{expr.name}'")
        return symbol.type

    # --------------------------------------------------------
    # llamada a función
    # --------------------------------------------------------

    def _analyze_call(self, expr: ast.CallExpr) -> str:
        func = self.symtab.resolve_global(expr.callee)
        if func is None or func.kind != "func":
            raise SemanticError(f"Función no declarada: '{expr.callee}'")

        params = func.params   # lo guarda symbol_table

        if len(expr.args) != len(params):
            raise SemanticError(
                f"Número incorrecto de argumentos en llamada a {expr.callee}"
            )

        # validar tipos de argumentos
        for i, arg_expr in enumerate(expr.args):
            arg_type = self._analyze_expr(arg_expr)
            param_type = params[i].param_type
            self._ensure_type_compatible(param_type, arg_type,
                                         f"Argumento {i+1} incompatible en llamada a {expr.callee}")

        return func.return_type if func.return_type else "void"

    # ============================================================
    #   utilidades de tipos
    # ============================================================

    def _require_type(self, found: str, expected: str, msg: str):
        if found != expected:
            raise SemanticError(msg + f" (se encontró '{found}')")

    def _require_numeric(self, t: str, msg: str):
        if t not in ("int", "float"):
            raise SemanticError(msg + f" (tipo '{t}')")

    def _ensure_type_compatible(self, expected: str, found: str, msg: str):
        # string solo con string
        if expected == "string" or found == "string":
            if expected != found:
                raise SemanticError(msg + f" → '{expected}' ≠ '{found}'")
            return

        # int → float promoción válida
        if expected == "float" and found == "int":
            return

        if expected != found:
            raise SemanticError(msg + f" → '{expected}' ≠ '{found}'")

