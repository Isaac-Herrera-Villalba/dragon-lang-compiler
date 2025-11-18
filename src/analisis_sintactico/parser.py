#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/analisis_sintactico/parser.py
------------------------------------------------------------
Descripción:
Módulo encargado del análisis sintáctico (parser) de Dragon-Lang.
Implementa un parser descendente recursivo que, a partir de la
secuencia de tokens generada por el analizador léxico, construye
un Árbol Sintáctico Abstracto (AST) según la gramática del lenguaje.

Este módulo:
- Valida la estructura sintáctica del programa.
- Construye nodos AST para funciones, sentencias y expresiones.
- Reporta errores sintácticos con información precisa de línea
  y columna, destacando el lexema problemático.

Constituye la segunda fase del pipeline de compilación.
------------------------------------------------------------
"""

from __future__ import annotations

from typing import List, Optional
from ..analisis_lexico.lexer import Token
from .ast import (
    Program,
    FunctionDecl,
    Param,
    BlockStmt,
    VarDeclStmt,
    ExprStmt,
    IfStmt,
    WhileStmt,
    DoWhileStmt,
    ForStmt,
    ReturnStmt,
    PrintStmt,
    ReadStmt,
    LiteralExpr,
    VarExpr,
    UnaryExpr,
    BinaryExpr,
    GroupingExpr,
    AssignmentExpr,
    Expr,
    Stmt,
    CallExpr,
)


class ParseError(Exception):
    """
    Excepción especializada para errores sintácticos.

    Incluye:
    - mensaje descriptivo del error
    - token donde se detectó el problema
    - código fuente completo para poder resaltar la línea y columna
    """

    def __init__(self, message: str, token: Token, source: str) -> None:
        self.message = message
        self.token = token
        self.source = source
        super().__init__(self.__str__())

    def __str__(self):
        line = self.token.line
        col = self.token.column
        lines = self.source.splitlines()
        txt = lines[line - 1] if 1 <= line <= len(lines) else ""
        caret = " " * (col - 1) + "^"

        return (
            f"Error sintáctico: {self.message}\n"
            f" --> Línea {line}, Columna {col}\n"
            f"    {line:>3} | {txt}\n"
            f"        | {caret}"
        )


class Parser:
    """
    Parser descendente recursivo para Dragon-Lang.

    Trabaja sobre una lista de tokens y construye un AST de alto nivel:
    - Program: lista de funciones
    - FunctionDecl: cuerpo, parámetros
    - Sentencias de control de flujo
    - Expresiones con precedencia y asociatividad

    No realiza análisis de tipos ni verificación semántica; eso se delega
    al módulo de análisis semántico.
    """

    def __init__(self, tokens: List[Token], source: str):
        self.tokens = tokens
        self.source = source
        self.current = 0

        # Conjunto de palabras clave para distinguir identificadores
        self.keywords = {
            "func", "int", "float", "bool", "string",
            "if", "else", "while", "do", "for",
            "return", "print", "read",
            "true", "false",
        }

    # ===========================================================
    # Helpers básicos de navegación sobre la lista de tokens
    # ===========================================================

    def is_at_end(self) -> bool:
        """Devuelve True si se alcanzó el token EOF."""
        return self.peek().lexeme == "EOF"

    def peek(self) -> Token:
        """Devuelve el token actual sin consumirlo."""
        return self.tokens[self.current]

    def previous(self) -> Token:
        """Devuelve el último token consumido."""
        return self.tokens[self.current - 1]

    def advance(self) -> Token:
        """
        Consume el token actual y avanza al siguiente.
        Devuelve el token recién consumido.
        """
        if not self.is_at_end():
            self.current += 1
        return self.previous()

    def check(self, lex: str) -> bool:
        """
        Comprueba si el token actual coincide con el lexema indicado,
        sin consumirlo.
        """
        if self.is_at_end():
            return False
        return self.peek().lexeme == lex

    def match(self, *lexemes: str) -> bool:
        """
        Si el token actual es uno de los lexemas dados, lo consume
        y devuelve True; en caso contrario devuelve False.
        """
        if self.is_at_end():
            return False
        if self.peek().lexeme in lexemes:
            self.advance()
            return True
        return False

    def consume(self, lex: str, msg: str) -> Token:
        """
        Consume el token esperado (por lexema) o lanza un ParseError
        con el mensaje proporcionado.
        """
        if self.check(lex):
            return self.advance()
        raise self.error(self.peek(), msg)

    def error(self, tok: Token, msg: str) -> ParseError:
        """Crea una instancia de ParseError con contexto de fuente."""
        return ParseError(msg, tok, self.source)

    # ===========================================================
    # PROGRAM
    # ===========================================================

    def parse_program(self) -> Program:
        """
        Punto de entrada del parser.

        Un programa es una secuencia de declaraciones de funciones
        hasta llegar a EOF.
        """
        funcs: List[FunctionDecl] = []
        while not self.is_at_end():
            if self.check("EOF"):
                break
            funcs.append(self.function_decl())
        return Program(funcs)

    # ===========================================================
    # FUNCTIONS
    # ===========================================================

    def function_decl(self) -> FunctionDecl:
        """
        Analiza una declaración de función con la forma:

            func nombre(tipo1 p1, tipo2 p2, ...) {
                ...
            }
        """
        self.consume("func", "Se esperaba 'func' al inicio de una función.")

        name_tok = self.consume_identifier("Se esperaba nombre de función.")
        func_name = name_tok.lexeme

        self.consume("(", "Se esperaba '(' en declaración de función.")

        params: List[Param] = []
        if not self.check(")"):
            params = self.param_list()

        self.consume(")", "Se esperaba ')' en declaración de función.")

        body = self.block()
        return FunctionDecl(name=func_name, params=params, body=body)

    def param_list(self) -> List[Param]:
        """
        Analiza una lista de parámetros separada por comas:

            int a, float b, bool c
        """
        params = [self.param()]
        while self.match(","):
            params.append(self.param())
        return params

    def param(self) -> Param:
        """Analiza un parámetro individual: tipo + nombre."""
        type_tok = self.consume_type("Se esperaba tipo de parámetro.")
        name_tok = self.consume_identifier("Se esperaba nombre de parámetro.")
        return Param(type_tok.lexeme, name_tok.lexeme)

    # ===========================================================
    # DECLARATIONS / STATEMENTS
    # ===========================================================

    def declaration(self) -> Stmt:
        """
        Punto de entrada para declaraciones dentro de un bloque.

        Puede ser:
        - Declaración de variable
        - O cualquier tipo de sentencia
        """
        if self.check("int") or self.check("float") or self.check("bool") or self.check("string"):
            return self.var_declaration()
        return self.statement()

    def var_declaration(self) -> VarDeclStmt:
        """
        Declaración de variable con inicialización opcional:

            int x;
            float y = 3.14;
        """
        type_tok = self.advance()
        var_type = type_tok.lexeme

        name_tok = self.consume_identifier("Se esperaba nombre de variable.")
        var_name = name_tok.lexeme

        init: Optional[Expr] = None
        if self.match("="):
            init = self.expression()

        self.consume(";", "Se esperaba ';' después de declaración.")
        return VarDeclStmt(var_type, var_name, init)

    def statement(self) -> Stmt:
        """
        Analiza una sentencia genérica, que puede ser:
        - Bloque
        - if / while / do-while / for
        - print / read
        - return
        - o una expresión terminada en ';'
        """
        # Bloque → NO consumir aquí la {
        if self.check("{"):
            return self.block()

        if self.match("if"):
            return self.if_statement()

        if self.match("while"):
            return self.while_statement()

        if self.match("do"):
            return self.do_while_statement()

        if self.match("for"):
            return self.for_statement()

        if self.match("print"):
            return self.print_statement()

        if self.match("read"):
            return self.read_statement()

        if self.match("return"):
            return self.return_statement()

        return self.expr_statement()

    # ===========================================================
    # BLOCK
    # ===========================================================

    def block(self) -> BlockStmt:
        """
        Analiza un bloque de sentencias:

            {
                ...
            }
        """
        self.consume("{", "Se esperaba '{'.")
        stmts: List[Stmt] = []

        while not self.check("}") and not self.is_at_end():
            stmts.append(self.declaration())

        self.consume("}", "Se esperaba '}' al final del bloque.")
        return BlockStmt(stmts)

    # ===========================================================
    # IF, WHILE, DO-WHILE, FOR
    # ===========================================================

    def if_statement(self) -> IfStmt:
        """Analiza una sentencia if (posiblemente con else)."""
        self.consume("(", "Se esperaba '(' después de 'if'.")
        cond = self.expression()
        self.consume(")", "Se esperaba ')' en condición de if.")
        then_b = self.statement()
        else_b: Optional[Stmt] = None
        if self.match("else"):
            else_b = self.statement()
        return IfStmt(cond, then_b, else_b)

    def while_statement(self) -> WhileStmt:
        """Analiza un bucle while clásico."""
        self.consume("(", "Se esperaba '(' después de 'while'.")
        cond = self.expression()
        self.consume(")", "Se esperaba ')' en while.")
        body = self.statement()
        return WhileStmt(cond, body)

    def do_while_statement(self) -> DoWhileStmt:
        """Analiza un bucle do-while."""
        body = self.statement()
        self.consume("while", "Se esperaba 'while' después de 'do'.")
        self.consume("(", "Se esperaba '(' después de while.")
        cond = self.expression()
        self.consume(")", "Se esperaba ')'.")
        self.consume(";", "Se esperaba ';' en do-while.")
        return DoWhileStmt(body, cond)

    def for_statement(self) -> ForStmt:
        """
        Analiza un bucle for de la forma:

            for ( init ; cond ; update ) stmt
        donde cada componente es opcional.
        """
        self.consume("(", "Se esperaba '(' en for.")

        # init
        if not self.check(";"):
            if self.check("int") or self.check("float") or self.check("bool") or self.check("string"):
                init: Optional[Stmt] = self.var_declaration()
            else:
                init_expr = self.expression()
                self.consume(";", "Se esperaba ';' después de init.")
                init = ExprStmt(init_expr)
        else:
            self.consume(";", "")
            init = None

        # cond
        if not self.check(";"):
            cond = self.expression()
            self.consume(";", "Se esperaba ';' después de condición.")
        else:
            self.consume(";", "")
            cond = None

        # update
        if not self.check(")"):
            update = self.expression()
        else:
            update = None

        self.consume(")", "Se esperaba ')' en for.")
        body = self.statement()

        return ForStmt(init, cond, update, body)

    # ===========================================================
    # PRINT / READ / RETURN / EXPR-STMT
    # ===========================================================

    def print_statement(self) -> PrintStmt:
        """Analiza la sentencia print expr;"""
        e = self.expression()
        self.consume(";", "Se esperaba ';' en print.")
        return PrintStmt(e)

    def read_statement(self) -> ReadStmt:
        """Analiza la sentencia read identificador;"""
        name_tok = self.consume_identifier("Se esperaba nombre en read.")
        self.consume(";", "Se esperaba ';' en read.")
        return ReadStmt(VarExpr(name_tok.lexeme))

    def return_statement(self) -> ReturnStmt:
        """Analiza la sentencia return; o return expr;"""
        if not self.check(";"):
            val = self.expression()
        else:
            val = None
        self.consume(";", "Se esperaba ';' en return.")
        return ReturnStmt(val)

    def expr_statement(self) -> ExprStmt:
        """Analiza una sentencia de expresión terminada en ';'."""
        e = self.expression()
        self.consume(";", "Se esperaba ';'.")
        return ExprStmt(e)

    # ===========================================================
    # EXPRESSIONS (jerarquía de precedencias)
    # ===========================================================

    def expression(self) -> Expr:
        """Entrada general para expresiones: empieza por asignación."""
        return self.assignment()

    def assignment(self) -> Expr:
        """
        Analiza expresiones de asignación:

            x = expr

        Si no hay '=', se interpreta como una expresión lógica (or_expr).
        """
        expr = self.or_expr()
        if self.match("="):
            value = self.assignment()
            if isinstance(expr, VarExpr):
                return AssignmentExpr(expr.name, value)
            raise self.error(self.previous(), "La izquierda de '=' debe ser variable.")
        return expr

    def or_expr(self) -> Expr:
        """Expresiones con operador lógico OR (||)."""
        expr = self.and_expr()
        while self.match("||"):
            op = self.previous().lexeme
            right = self.and_expr()
            expr = BinaryExpr(expr, op, right)
        return expr

    def and_expr(self) -> Expr:
        """Expresiones con operador lógico AND (&&)."""
        expr = self.equality()
        while self.match("&&"):
            op = self.previous().lexeme
            right = self.equality()
            expr = BinaryExpr(expr, op, right)
        return expr

    def equality(self) -> Expr:
        """Operadores de igualdad: == y !=."""
        expr = self.comparison()
        while self.match("==", "!="):
            op = self.previous().lexeme
            right = self.comparison()
            expr = BinaryExpr(expr, op, right)
        return expr

    def comparison(self) -> Expr:
        """Operadores relacionales: <, <=, >, >=."""
        expr = self.term()
        while self.match("<", "<=", ">", ">="):
            op = self.previous().lexeme
            right = self.term()
            expr = BinaryExpr(expr, op, right)
        return expr

    def term(self) -> Expr:
        """Suma y resta: +, -."""
        expr = self.factor()
        while self.match("+", "-"):
            op = self.previous().lexeme
            right = self.factor()
            expr = BinaryExpr(expr, op, right)
        return expr

    def factor(self) -> Expr:
        """Multiplicación, división y módulo: *, /, %."""
        expr = self.unary()
        while self.match("*", "/", "%"):
            op = self.previous().lexeme
            right = self.unary()
            expr = BinaryExpr(expr, op, right)
        return expr

    def unary(self) -> Expr:
        """Operadores unarios: ! y -."""
        if self.match("!", "-"):
            op = self.previous().lexeme
            right = self.unary()
            return UnaryExpr(op, right)
        return self.primary()

    # ===========================================================
    # PRIMARY (literales, identificadores, agrupación)
    # ===========================================================
    def primary(self):
        if self.is_at_end():
            raise self.error(self.peek(), "Expresión incompleta.")

        tok = self.peek()
        lex = tok.lexeme

        # números
        if lex.replace('.', '', 1).isdigit():
            self.advance()
            if "." in lex:
                return LiteralExpr(float(lex))
            return LiteralExpr(int(lex))

        # true/false
        if lex == "true":
            self.advance()
            return LiteralExpr(True)
        if lex == "false":
            self.advance()
            return LiteralExpr(False)

        # strings
        if lex.startswith('"') and lex.endswith('"'):
            self.advance()
            return LiteralExpr(lex[1:-1])

        # agrupación
        if self.match("("):
            expr = self.expression()
            self.consume(")", "Se esperaba ')'.")
            return GroupingExpr(expr)

        # IDENTIFICADOR O LLAMADA A FUNCIÓN
        if lex not in self.keywords and (lex[0].isalpha() or lex[0] == "_"):
            self.advance()
            name = lex

            # llamada a función
            if self.match("("):
                args = []
                if not self.check(")"):
                    args.append(self.expression())
                    while self.match(","):
                        args.append(self.expression())
                self.consume(")", "Se esperaba ')' en llamada a función.")
                return CallExpr(name, args)

            # si no hay '(', es variable
            return VarExpr(name)

        raise self.error(tok, f"Expresión inválida: '{lex}'.")

    # ===========================================================
    # Utilities para identificadores y tipos
    # ===========================================================

    def consume_identifier(self, msg: str) -> Token:
        """
        Consume un identificador válido (no palabra clave) o lanza error.
        """
        tok = self.peek()
        lex = tok.lexeme

        if lex not in self.keywords and (lex[0].isalpha() or lex[0] == "_"):
            self.advance()
            return tok

        raise self.error(tok, msg)

    def consume_type(self, msg: str) -> Token:
        """
        Consume un tipo básico válido: int, float, bool, string.
        """
        tok = self.peek()
        if tok.lexeme in ("int", "float", "bool", "string"):
            self.advance()
            return tok
        raise self.error(tok, msg)


def parse(tokens: List[Token], source: str) -> Program:
    """
    Función de conveniencia que construye un Parser
    y devuelve el AST completo del programa.
    """
    return Parser(tokens, source).parse_program()

