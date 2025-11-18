#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/analisis_sintactico/ast.py
------------------------------------------------------------
Definición del Árbol Sintáctico Abstracto (AST) para el
mini-lenguaje "Dragon".

Soporta:
- Funciones con parámetros: func f(int a, float b) { ... }
- Llamadas a funciones: f(x, y)
- Tipos de variables: int, float, bool, string
------------------------------------------------------------
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Union


# ============================================================
#   Nodos base
# ============================================================

class Node:
    """Nodo base del AST."""
    pass


class Stmt(Node):
    """Nodo base para sentencias."""
    pass


class Expr(Node):
    """Nodo base para expresiones."""
    pass


# ============================================================
#   Programa / Funciones
# ============================================================

@dataclass
class Program(Node):
    functions: List["FunctionDecl"]


@dataclass
class Param(Node):
    """Parámetro de función: tipo + nombre."""
    param_type: str   # "int", "float", "bool", "string"
    name: str


@dataclass
class FunctionDecl(Node):
    """
    Declaración de función.

    Ejemplos de sintaxis que soportaremos en el parser:
        func main() {
            ...
        }

        func factorial(int n) {
            ...
        }
    """
    name: str
    params: List[Param]
    body: "BlockStmt"


# ============================================================
#   Sentencias
# ============================================================

@dataclass
class BlockStmt(Stmt):
    statements: List[Stmt]


@dataclass
class VarDeclStmt(Stmt):
    var_type: str        # "int", "float", "bool", "string"
    name: str
    initializer: Optional[Expr]


@dataclass
class ExprStmt(Stmt):
    expr: Expr


@dataclass
class IfStmt(Stmt):
    condition: Expr
    then_branch: Stmt
    else_branch: Optional[Stmt]


@dataclass
class WhileStmt(Stmt):
    condition: Expr
    body: Stmt


@dataclass
class DoWhileStmt(Stmt):
    body: Stmt
    condition: Expr


@dataclass
class ForStmt(Stmt):
    init: Optional[Stmt]        # VarDeclStmt, ExprStmt o None
    condition: Optional[Expr]
    update: Optional[Expr]
    body: Stmt


@dataclass
class ReturnStmt(Stmt):
    value: Optional[Expr]       # return; o return expr;


@dataclass
class PrintStmt(Stmt):
    expr: Expr


@dataclass
class ReadStmt(Stmt):
    target: "VarExpr"           # read x;


# ============================================================
#   Expresiones
# ============================================================

@dataclass
class LiteralExpr(Expr):
    # Soporta literales: int, float, bool, string
    value: Union[int, float, bool, str]


@dataclass
class VarExpr(Expr):
    name: str


@dataclass
class UnaryExpr(Expr):
    op: str
    operand: Expr


@dataclass
class BinaryExpr(Expr):
    left: Expr
    op: str
    right: Expr


@dataclass
class GroupingExpr(Expr):
    expr: Expr


@dataclass
class AssignmentExpr(Expr):
    name: str
    value: Expr


@dataclass
class CallExpr(Expr):
    """
    Llamada a función:

        f(x, y, 3.14)

    callee: nombre de la función
    args: lista de expresiones de argumentos
    """
    callee: str
    args: List[Expr]

