#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parser.py corregido
Parser descendente recursivo para Dragon-lang, con:

- funciones con parámetros
- strings
- floats, ints, bools
- if / while / do-while / for
- bloques correctos
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
)


class ParseError(Exception):
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
    def __init__(self, tokens: List[Token], source: str):
        self.tokens = tokens
        self.source = source
        self.current = 0

        self.keywords = {
            "func", "int", "float", "bool", "string",
            "if", "else", "while", "do", "for",
            "return", "print", "read",
            "true", "false",
        }

    # -------------- Helpers -------------------

    def is_at_end(self):
        return self.peek().lexeme == "EOF"

    def peek(self):
        return self.tokens[self.current]

    def previous(self):
        return self.tokens[self.current - 1]

    def advance(self):
        if not self.is_at_end():
            self.current += 1
        return self.previous()

    def check(self, lex):
        if self.is_at_end():
            return False
        return self.peek().lexeme == lex

    def match(self, *lexemes):
        if self.is_at_end():
            return False
        if self.peek().lexeme in lexemes:
            self.advance()
            return True
        return False

    def consume(self, lex, msg):
        if self.check(lex):
            return self.advance()
        raise self.error(self.peek(), msg)

    def error(self, tok: Token, msg: str):
        return ParseError(msg, tok, self.source)

    # ===========================================
    # PROGRAM
    # ===========================================

    def parse_program(self):
        funcs = []
        while not self.is_at_end():
            if self.check("EOF"):
                break
            funcs.append(self.function_decl())
        return Program(funcs)

    # ===========================================
    # FUNCTIONS
    # ===========================================

    def function_decl(self):
        self.consume("func", "Se esperaba 'func' al inicio de una función.")

        name_tok = self.consume_identifier("Se esperaba nombre de función.")
        func_name = name_tok.lexeme

        self.consume("(", "Se esperaba '(' en declaración de función.")

        params = []
        if not self.check(")"):
            params = self.param_list()

        self.consume(")", "Se esperaba ')' en declaración de función.")

        body = self.block()
        return FunctionDecl(name=func_name, params=params, body=body)

    def param_list(self):
        params = [self.param()]
        while self.match(","):
            params.append(self.param())
        return params

    def param(self):
        type_tok = self.consume_type("Se esperaba tipo de parámetro.")
        name_tok = self.consume_identifier("Se esperaba nombre de parámetro.")
        return Param(type_tok.lexeme, name_tok.lexeme)

    # ===========================================
    # DECLARATIONS / STATEMENTS
    # ===========================================

    def declaration(self):
        if self.check("int") or self.check("float") or self.check("bool") or self.check("string"):
            return self.var_declaration()
        return self.statement()

    def var_declaration(self):
        type_tok = self.advance()
        var_type = type_tok.lexeme

        name_tok = self.consume_identifier("Se esperaba nombre de variable.")
        var_name = name_tok.lexeme

        init = None
        if self.match("="):
            init = self.expression()

        self.consume(";", "Se esperaba ';' después de declaración.")
        return VarDeclStmt(var_type, var_name, init)

    def statement(self):
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

    # ===========================================
    # BLOCK
    # ===========================================

    def block(self):
        self.consume("{", "Se esperaba '{'.")
        stmts = []

        while not self.check("}") and not self.is_at_end():
            stmts.append(self.declaration())

        self.consume("}", "Se esperaba '}' al final del bloque.")
        return BlockStmt(stmts)

    # ===========================================
    # IF, WHILE, DO-WHILE, FOR
    # ===========================================

    def if_statement(self):
        self.consume("(", "Se esperaba '(' después de 'if'.")
        cond = self.expression()
        self.consume(")", "Se esperaba ')' en condición de if.")
        then_b = self.statement()
        else_b = None
        if self.match("else"):
            else_b = self.statement()
        return IfStmt(cond, then_b, else_b)

    def while_statement(self):
        self.consume("(", "Se esperaba '(' después de 'while'.")
        cond = self.expression()
        self.consume(")", "Se esperaba ')' en while.")
        body = self.statement()
        return WhileStmt(cond, body)

    def do_while_statement(self):
        body = self.statement()
        self.consume("while", "Se esperaba 'while' después de 'do'.")
        self.consume("(", "Se esperaba '(' después de while.")
        cond = self.expression()
        self.consume(")", "Se esperaba ')'.")
        self.consume(";", "Se esperaba ';' en do-while.")
        return DoWhileStmt(body, cond)

    def for_statement(self):
        self.consume("(", "Se esperaba '(' en for.")

        # init
        if not self.check(";"):
            if self.check("int") or self.check("float") or self.check("bool") or self.check("string"):
                init = self.var_declaration()
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

    # ===========================================
    # PRINT / READ / RETURN
    # ===========================================

    def print_statement(self):
        e = self.expression()
        self.consume(";", "Se esperaba ';' en print.")
        return PrintStmt(e)

    def read_statement(self):
        name_tok = self.consume_identifier("Se esperaba nombre en read.")
        self.consume(";", "Se esperaba ';' en read.")
        return ReadStmt(VarExpr(name_tok.lexeme))

    def return_statement(self):
        if not self.check(";"):
            val = self.expression()
        else:
            val = None
        self.consume(";", "Se esperaba ';' en return.")
        return ReturnStmt(val)

    def expr_statement(self):
        e = self.expression()
        self.consume(";", "Se esperaba ';'.")
        return ExprStmt(e)

    # ===========================================
    # EXPRESSIONS
    # ===========================================

    def expression(self):
        return self.assignment()

    def assignment(self):
        expr = self.or_expr()
        if self.match("="):
            value = self.assignment()
            if isinstance(expr, VarExpr):
                return AssignmentExpr(expr.name, value)
            raise self.error(self.previous(), "La izquierda de '=' debe ser variable.")
        return expr

    def or_expr(self):
        expr = self.and_expr()
        while self.match("||"):
            op = self.previous().lexeme
            right = self.and_expr()
            expr = BinaryExpr(expr, op, right)
        return expr

    def and_expr(self):
        expr = self.equality()
        while self.match("&&"):
            op = self.previous().lexeme
            right = self.equality()
            expr = BinaryExpr(expr, op, right)
        return expr

    def equality(self):
        expr = self.comparison()
        while self.match("==", "!="):
            op = self.previous().lexeme
            right = self.comparison()
            expr = BinaryExpr(expr, op, right)
        return expr

    def comparison(self):
        expr = self.term()
        while self.match("<", "<=", ">", ">="):
            op = self.previous().lexeme
            right = self.term()
            expr = BinaryExpr(expr, op, right)
        return expr

    def term(self):
        expr = self.factor()
        while self.match("+", "-"):
            op = self.previous().lexeme
            right = self.factor()
            expr = BinaryExpr(expr, op, right)
        return expr

    def factor(self):
        expr = self.unary()
        while self.match("*", "/", "%"):
            op = self.previous().lexeme
            right = self.unary()
            expr = BinaryExpr(expr, op, right)
        return expr

    def unary(self):
        if self.match("!", "-"):
            op = self.previous().lexeme
            right = self.unary()
            return UnaryExpr(op, right)
        return self.primary()

    # ===========================================
    # PRIMARY (con soporte correcto de strings)
    # ===========================================

    def primary(self):
        if self.is_at_end():
            raise self.error(self.peek(), "Expresión incompleta.")

        tok = self.peek()
        lex = tok.lexeme

        # números (int o float)
        if lex.replace('.', '', 1).isdigit():
            self.advance()
            if "." in lex:
                return LiteralExpr(float(lex))
            return LiteralExpr(int(lex))

        # TRUE / FALSE
        if lex == "true":
            self.advance()
            return LiteralExpr(True)
        if lex == "false":
            self.advance()
            return LiteralExpr(False)

        # STRING
        if lex.startswith('"') and lex.endswith('"'):
            self.advance()
            return LiteralExpr(lex[1:-1])

        # Agrupación
        if self.match("("):
            expr = self.expression()
            self.consume(")", "Se esperaba ')'.")
            return GroupingExpr(expr)

        # Identificador
        if lex not in self.keywords and (lex[0].isalpha() or lex[0] == "_"):
            self.advance()
            return VarExpr(lex)

        raise self.error(tok, f"Expresión inválida: '{lex}'.")


    # ===========================================
    # Utilities
    # ===========================================

    def consume_identifier(self, msg):
        tok = self.peek()
        lex = tok.lexeme

        if lex not in self.keywords and (lex[0].isalpha() or lex[0] == "_"):
            self.advance()
            return tok

        raise self.error(tok, msg)

    def consume_type(self, msg):
        tok = self.peek()
        if tok.lexeme in ("int", "float", "bool", "string"):
            self.advance()
            return tok
        raise self.error(tok, msg)


def parse(tokens, source):
    return Parser(tokens, source).parse_program()

