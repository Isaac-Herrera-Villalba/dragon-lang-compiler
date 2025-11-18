#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/analisis_sintactico/ast.py
------------------------------------------------------------
Descripción:
Definición del Árbol Sintáctico Abstracto (AST) para el
lenguaje Dragon-Lang.

Este módulo modela la estructura lógica de un programa mediante
clases de Python que representan:
- Programas completos (lista de funciones)
- Declaraciones de funciones y parámetros
- Sentencias (bloques, declaraciones, control de flujo, I/O, etc.)
- Expresiones (literales, variables, operaciones, llamadas, etc.)

El AST es la representación intermedia de alto nivel que será
consumida por las fases posteriores:
- análisis semántico
- generación de código intermedio (IR/TAC)
------------------------------------------------------------
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Union


# ============================================================
#   Nodos base
# ============================================================

class Node:
    """
    Nodo base del AST.

    Sirve como superclase común para todos los nodos del árbol
    (sentencias y expresiones), permitiendo tratarlos de forma
    polimórfica en las fases posteriores del compilador.
    """
    pass


class Stmt(Node):
    """
    Nodo base para todas las sentencias (statements).

    Ejemplos:
    - declaraciones de variables
    - bloques de código
    - sentencias if, while, for, do-while
    - sentencias de entrada/salida
    - sentencias de retorno
    """
    pass


class Expr(Node):
    """
    Nodo base para todas las expresiones.

    Ejemplos:
    - literales (int, float, bool, string)
    - variables
    - operaciones unarias y binarias
    - asignaciones
    - llamadas a funciones
    """
    pass


# ============================================================
#   Programa / Funciones
# ============================================================

@dataclass
class Program(Node):
    """
    Representa un programa completo en Dragon-Lang.

    Contiene una lista de declaraciones de funciones, donde
    normalmente debe existir al menos una función `main` que
    actúa como punto de entrada.
    """
    functions: List["FunctionDecl"]


@dataclass
class Param(Node):
    """
    Parámetro de función: tipo + nombre.

    Ejemplo:
        int n
        float x
    """
    param_type: str   # "int", "float", "bool", "string"
    name: str


@dataclass
class FunctionDecl(Node):
    """
    Declaración de función.

    Sintaxis soportada en el parser:
        func main() {
            ...
        }

        func factorial(int n) {
            ...
        }

    Atributos:
    - name: nombre de la función
    - params: lista de parámetros tipados
    - body: bloque de sentencias que conforman el cuerpo
    """
    name: str
    params: List[Param]
    body: "BlockStmt"


# ============================================================
#   Sentencias
# ============================================================

@dataclass
class BlockStmt(Stmt):
    """
    Bloque de sentencias encerrado entre llaves:

        {
            stmt1;
            stmt2;
            ...
        }

    Modela un nuevo ámbito (scope) en el análisis semántico.
    """
    statements: List[Stmt]


@dataclass
class VarDeclStmt(Stmt):
    """
    Declaración de variable con inicialización opcional:

        int x;
        float y = 3.14;

    Atributos:
    - var_type: tipo de la variable
    - name: identificador de la variable
    - initializer: expresión opcional de inicialización
    """
    var_type: str        # "int", "float", "bool", "string"
    name: str
    initializer: Optional[Expr]


@dataclass
class ExprStmt(Stmt):
    """
    Sentencia que consiste únicamente en una expresión
    seguida de punto y coma:

        x = 10;
        foo(3, 4);
    """
    expr: Expr


@dataclass
class IfStmt(Stmt):
    """
    Sentencia condicional:

        if (condición) stmt
        else stmt

    Atributos:
    - condition: expresión booleana
    - then_branch: sentencia ejecutada si la condición es verdadera
    - else_branch: sentencia opcional para el caso contrario
    """
    condition: Expr
    then_branch: Stmt
    else_branch: Optional[Stmt]


@dataclass
class WhileStmt(Stmt):
    """
    Bucle while clásico:

        while (condición) stmt

    La condición se evalúa antes de cada iteración.
    """
    condition: Expr
    body: Stmt


@dataclass
class DoWhileStmt(Stmt):
    """
    Bucle do-while:

        do stmt
        while (condición);

    La condición se evalúa después de ejecutar el cuerpo al menos una vez.
    """
    body: Stmt
    condition: Expr


@dataclass
class ForStmt(Stmt):
    """
    Bucle for generalizado:

        for (init; condition; update) body

    Atributos:
    - init: sentencia inicial (declaración o expresión) o None
    - condition: expresión booleana o None (equivale a true)
    - update: expresión de actualización o None
    - body: sentencia que representa el cuerpo del bucle
    """
    init: Optional[Stmt]        # VarDeclStmt, ExprStmt o None
    condition: Optional[Expr]
    update: Optional[Expr]
    body: Stmt


@dataclass
class ReturnStmt(Stmt):
    """
    Sentencia de retorno de función:

        return;
        return expr;

    value es None cuando no se retorna ningún valor explícito.
    """
    value: Optional[Expr]       # return; o return expr;


@dataclass
class PrintStmt(Stmt):
    """
    Sentencia de salida:

        print expr;

    Imprime el valor de la expresión en la salida estándar.
    """
    expr: Expr


@dataclass
class ReadStmt(Stmt):
    """
    Sentencia de entrada:

        read x;

    Lee desde la entrada estándar y almacena el valor en
    la variable indicada (VarExpr).
    """
    target: "VarExpr"           # read x;


# ============================================================
#   Expresiones
# ============================================================

@dataclass
class LiteralExpr(Expr):
    """
    Expresión literal.

    Soporta:
    - int
    - float
    - bool
    - string
    """
    value: Union[int, float, bool, str]


@dataclass
class VarExpr(Expr):
    """
    Uso de una variable en una expresión.

    Contiene únicamente el nombre de la variable.
    """
    name: str


@dataclass
class UnaryExpr(Expr):
    """
    Expresión unaria:

        -expr
        !expr

    Atributos:
    - op: operador unario ("-" o "!")
    - operand: expresión objetivo
    """
    op: str
    operand: Expr


@dataclass
class BinaryExpr(Expr):
    """
    Expresión binaria:

        expr op expr

    Ejemplos:
    - expr aritméticas: +, -, *, /, %
    - comparaciones: ==, !=, <, <=, >, >=
    - lógicas: &&, ||
    """
    left: Expr
    op: str
    right: Expr


@dataclass
class GroupingExpr(Expr):
    """
    Expresión agrupada entre paréntesis:

        (expr)

    Se utiliza para controlar la precedencia en el AST.
    """
    expr: Expr


@dataclass
class AssignmentExpr(Expr):
    """
    Expresión de asignación:

        nombre = expr

    Atributos:
    - name: identificador de la variable
    - value: expresión a asignar
    """
    name: str
    value: Expr


@dataclass
class CallExpr(Expr):
    """
    Llamada a función:

        f(x, y, 3.14)

    Atributos:
    - callee: nombre de la función
    - args: lista de expresiones de argumentos
    """
    callee: str
    args: List[Expr]

