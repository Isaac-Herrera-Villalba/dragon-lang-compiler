#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/analisis_semantico/semantic.py
------------------------------------------------------------
Descripción:
Módulo encargado del análisis semántico del lenguaje Dragon-Lang.

Este análisis valida:
- Uso correcto de variables (declaración previa, tipos compatibles).
- Tipos en expresiones aritméticas, lógicas y comparaciones.
- Tipos de parámetros en llamadas a funciones.
- Consistencia de tipos de retorno en funciones.
- Reglas de alcance mediante una tabla de símbolos con scopes anidados.

Su propósito es garantizar que el programa sea semánticamente válido
antes de generar código intermedio (TAC).
------------------------------------------------------------
"""

from __future__ import annotations
from typing import Optional, List

from .symbol_table import SymbolTable, SymbolTableError
from ..analisis_sintactico import ast


# ============================================================
#   Excepción para errores semánticos
# ============================================================

class SemanticError(Exception):
    """
    Representa errores semánticos detectados durante el análisis,
    tales como:
    - Uso de variables no declaradas
    - Operaciones entre tipos incompatibles
    - Funciones llamadas con argumentos incorrectos
    - Inconsistencias en tipos de retorno

    En general, cualquier violación del significado correcto del
    programa se reporta con esta excepción.
    """
    pass


# ============================================================
#   Analizador Semántico
# ============================================================

class SemanticAnalyzer:
    """
    Clase principal encargada de realizar el análisis semántico.

    Utiliza una tabla de símbolos para rastrear variables, parámetros
    y funciones, revisando tipos y reglas semánticas del lenguaje.
    """

    def __init__(self) -> None:
        # Tabla de símbolos global y scopes anidados
        self.symtab = SymbolTable()
        self.current_function: Optional[str] = None
        self.current_return_type: Optional[str] = None

    # --------------------------------------------------------
    # Entrada principal del análisis semántico
    # --------------------------------------------------------

    def analyze(self, program: ast.Program) -> None:
        """
        Recorre el programa completo, registrando funciones,
        luego analizando cada una.

        Parámetros:
        - program: nodo AST Program.

        Pasos:
        1. Registrar todas las funciones en el scope global.
        2. Analizar cada función en detalle.
        """
        # Registrar funciones en ámbito global
        for func in program.functions:
            try:
                self.symtab.define_func(func.name, return_type=None)
            except SymbolTableError as e:
                raise SemanticError(f"Función redeclarada: {func.name}. Detalle: {e}")

        # Analizar cada función (parámetros, cuerpo, retornos, etc.)
        for func in program.functions:
            self._analyze_function(func)

    # --------------------------------------------------------
    # Funciones y parámetros
    # --------------------------------------------------------

    def _analyze_function(self, func: ast.FunctionDecl) -> None:
        """
        Analiza una función completa:
        - Entra a su scope.
        - Declara parámetros.
        - Analiza el cuerpo.
        - Establece tipo de retorno inferido.
        """
        self.symtab.push_scope(func.name)
        self.current_function = func.name
        self.current_return_type = None

        # Declarar parámetros
        for p in func.params:
            try:
                self.symtab.define_var(p.name, p.param_type)
            except SymbolTableError:
                raise SemanticError(f"Parámetro redeclarado: {p.name}")

        # Analizar el cuerpo de la función
        self._analyze_stmt(func.body)

        # Salir del scope
        self.symtab.pop_scope()

        # Limpiar referencias
        self.current_function = None
        self.current_return_type = None

    # --------------------------------------------------------
    # Sentencias
    # --------------------------------------------------------

    def _analyze_stmt(self, stmt: ast.Stmt) -> None:
        """Analiza cualquier tipo de sentencia del AST."""
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
    # Declaración de variables
    # --------------------------------------------------------

    def _declare_var(self, stmt: ast.VarDeclStmt):
        """
        Declara una variable en el scope actual y valida su inicialización.
        """
        try:
            self.symtab.define_var(stmt.name, stmt.var_type)
        except SymbolTableError as e:
            raise SemanticError(str(e))

        if stmt.initializer:
            init_type = self._analyze_expr(stmt.initializer)
            self._ensure_type_compatible(
                stmt.var_type,
                init_type,
                f"Inicialización inválida de '{stmt.name}'"
            )

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
        """
        Analiza un ciclo for:
        - init (declaración o expresión)
        - condición
        - update
        - cuerpo
        """
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
        """
        Valida la consistencia del tipo de retorno dentro de una función.
        """
        if stmt.value is None:
            ret_type = "void"
        else:
            ret_type = self._analyze_expr(stmt.value)

        if self.current_return_type is None:
            # Primer return define tipo
            self.current_return_type = ret_type
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
        """
        Revisa que la variable objetivo exista.
        """
        symbol = self.symtab.resolve(stmt.target.name)
        if symbol is None or symbol.kind != "var":
            raise SemanticError(f"Variable no declarada usada en read: '{stmt.target.name}'")

    # --------------------------------------------------------
    # Expresiones
    # --------------------------------------------------------

    def _analyze_expr(self, expr: ast.Expr) -> str:
        """
        Retorna el tipo de la expresión, validando semánticamente su uso.
        """
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
    # Tipos de literales
    # --------------------------------------------------------

    def _infer_literal_type(self, value):
        """Determina el tipo del literal según Python."""
        if isinstance(value, bool): return "bool"
        if isinstance(value, int): return "int"
        if isinstance(value, float): return "float"
        if isinstance(value, str): return "string"
        raise SemanticError("Literal no soportado")

    # --------------------------------------------------------
    # Variables
    # --------------------------------------------------------

    def _lookup_var(self, name: str):
        """Busca el tipo de una variable en la tabla de símbolos."""
        symbol = self.symtab.resolve(name)
        if symbol is None:
            raise SemanticError(f"Variable no declarada: '{name}'")
        return symbol.type

    # --------------------------------------------------------
    # Unarias
    # --------------------------------------------------------

    def _analyze_unary(self, expr: ast.UnaryExpr) -> str:
        operand_type = self._analyze_expr(expr.operand)

        if expr.op == "-":
            self._require_numeric(operand_type, "El operador '-' requiere int o float")
            return operand_type

        if expr.op == "!":
            self._require_type(operand_type, "bool", "El operador '!' requiere bool")
            return "bool"

        raise SemanticError(f"Operador unario no soportado: {expr.op}")

    # --------------------------------------------------------
    # Binarias
    # --------------------------------------------------------

    def _analyze_binary(self, expr: ast.BinaryExpr) -> str:
        """
        Valida operadores aritméticos, comparaciones, lógicos y
        concatenación de strings.
        """
        left = self._analyze_expr(expr.left)
        right = self._analyze_expr(expr.right)
        op = expr.op

        # concatenación string
        if op == "+" and (left == "string" or right == "string"):
            return "string"

        # comparaciones
        if op in ("<", "<=", ">", ">=", "==", "!="):
            self._ensure_type_compatible(left, right, "Comparación entre tipos incompatibles")
            return "bool"

        # lógicos
        if op in ("&&", "||"):
            self._require_type(left, "bool", "Operador lógico requiere bool")
            self._require_type(right, "bool", "Operador lógico requiere bool")
            return "bool"

        # aritméticos
        if op in ("+", "-", "*", "/", "%"):
            self._require_numeric(left, "Operador aritmético inválido")
            self._require_numeric(right, "Operador aritmético inválido")

            if op == "%" and (left != "int" or right != "int"):
                raise SemanticError("El operador % requiere operandos int")

            if left == "float" or right == "float":
                return "float"
            return "int"

        raise SemanticError(f"Operador binario no soportado: {op}")

    # --------------------------------------------------------
    # Asignación
    # --------------------------------------------------------

    def _analyze_assignment(self, expr: ast.AssignmentExpr) -> str:
        symbol = self.symtab.resolve(expr.name)
        if symbol is None:
            raise SemanticError(f"Variable no declarada: '{expr.name}'")

        val_type = self._analyze_expr(expr.value)
        self._ensure_type_compatible(
            symbol.type,
            val_type,
            f"Asignación inválida a '{expr.name}'"
        )
        return symbol.type

    # --------------------------------------------------------
    # Llamada a función
    # --------------------------------------------------------

    def _analyze_call(self, expr: ast.CallExpr) -> str:
        """
        Valida que la función exista, que los argumentos coincidan
        con los tipos esperados y devuelve el tipo de retorno.
        """
        func = self.symtab.resolve_global(expr.callee)
        if func is None or func.kind != "func":
            raise SemanticError(f"Función no declarada: '{expr.callee}'")

        params = func.params

        if len(expr.args) != len(params):
            raise SemanticError(
                f"Número incorrecto de argumentos en llamada a {expr.callee}"
            )

        # verificar tipos
        for i, arg_expr in enumerate(expr.args):
            arg_type = self._analyze_expr(arg_expr)
            param_type = params[i].param_type
            self._ensure_type_compatible(
                param_type,
                arg_type,
                f"Argumento {i+1} incompatible en llamada a {expr.callee}"
            )

        return func.type if func.type else "void"

    # ============================================================
    #   Utilidades de tipos
    # ============================================================

    def _require_type(self, found: str, expected: str, msg: str):
        if found != expected:
            raise SemanticError(msg + f" (se encontró '{found}')")

    def _require_numeric(self, t: str, msg: str):
        if t not in ("int", "float"):
            raise SemanticError(msg + f" (tipo '{t}')")

    def _ensure_type_compatible(self, expected: str, found: str, msg: str):
        """
        Reglas de compatibilidad:
        - string solo con string
        - int puede ascender a float
        - tipos idénticos siempre compatibles
        """
        if expected == "string" or found == "string":
            if expected != found:
                raise SemanticError(msg + f" → '{expected}' ≠ '{found}'")
            return

        if expected == "float" and found == "int":
            return

        if expected != found:
            raise SemanticError(msg + f" → '{expected}' ≠ '{found}'")

