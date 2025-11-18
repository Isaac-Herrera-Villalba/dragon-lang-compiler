#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/analisis_lexico/lexer.py
------------------------------------------------------------
Lexer para Dragon-lang.
Soporta:
- Comentarios: '#' y /* ... */
- Identificadores (con soporte para caracteres españoles)
- Literales:
    int
    float
    string
    bool (true / false)
- Operadores:
    +  -  *  /  %  =
    == != <= >= < >
    && ||
    !
- Delimitadores: ( ) { } ; ,
- Manejo correcto de línea y columna
- Eliminación de BOM UTF-8
- Manejo robusto de whitespace
------------------------------------------------------------
"""

from __future__ import annotations
from dataclasses import dataclass
import re


# ============================================================
#   PATRONES PARA FLOAT E INT
# ============================================================

FLOAT_PATTERN = re.compile(
    r"""
    (                             # Grupo principal
        (?:\d+\.\d*)              # 3.14, 3.
      | (?:\.\d+)                 # .5
    )
    (?:[eE][+-]?\d+)?             # opcional notación científica
    |
    (?:\d+[eE][+-]?\d+)           # 3e10, 3E+5
    """,
    re.VERBOSE,
)

INT_PATTERN = re.compile(r"\d+")


# ============================================================
#   TOKEN
# ============================================================

@dataclass
class Token:
    lexeme: str
    line: int
    column: int


# ============================================================
#   ERROR LÉXICO
# ============================================================

class LexicalError(Exception):
    def __init__(self, message: str, line: int, column: int, source: str):
        self.message = message
        self.line = line
        self.column = column
        self.source = source
        super().__init__(self.__str__())

    def __str__(self):
        lines = self.source.splitlines()
        line_text = lines[self.line - 1] if 1 <= self.line <= len(lines) else ""
        caret = " " * (self.column - 1) + "^"

        return (
            f"Error léxico: {self.message}\n"
            f" --> Línea {self.line}, Columna {self.column}\n"
            f"    {self.line:>3} | {line_text}\n"
            f"        | {caret}"
        )


# ============================================================
#   TOKENIZER
# ============================================================

def tokenize(source: str):
    # eliminar BOM UTF-8 si existe
    if source.startswith("\ufeff"):
        source = source[1:]

    length = len(source)
    pos = 0
    line = 1
    column = 1

    def error(msg):
        raise LexicalError(msg, line, column, source)

    def current():
        return source[pos] if pos < length else "\0"

    while pos < length:
        char = current()

        # ----------------------------------------------------
        # Espacios en blanco
        # ----------------------------------------------------
        if char.isspace():
            if char == "\n":
                line += 1
                column = 1
            else:
                column += 1
            pos += 1
            continue

        # ----------------------------------------------------
        # Comentario de bloque /* ... */
        # ----------------------------------------------------
        if source.startswith("/*", pos):
            end = source.find("*/", pos + 2)
            if end == -1:
                error("Comentario de bloque sin cerrar.")

            block = source[pos:end + 2]

            # Actualizar líneas
            line += block.count("\n")
            if "\n" in block:
                column = len(block.split("\n")[-1]) + 1
            else:
                column += len(block)

            pos = end + 2
            continue

        # ----------------------------------------------------
        # Comentario de línea #
        # ----------------------------------------------------
        if char == "#":
            while pos < length and source[pos] != "\n":
                pos += 1
            continue

        # ----------------------------------------------------
        # Literales string
        # ----------------------------------------------------
        if char == '"':
            start_col = column
            start_pos = pos
            pos += 1
            column += 1

            value = ""
            while pos < length and source[pos] != '"':
                if source[pos] == "\n":
                    error("String no puede contener salto de línea.")
                value += source[pos]
                pos += 1
                column += 1

            if pos >= length:
                error("String sin cerrar.")

            pos += 1
            column += 1
            yield Token(f'"{value}"', line, start_col)
            continue

        # ----------------------------------------------------
        # FLOAT
        # ----------------------------------------------------
        m = FLOAT_PATTERN.match(source, pos)
        if m:
            lex = m.group(0)
            start_col = column
            pos += len(lex)
            column += len(lex)
            yield Token(lex, line, start_col)
            continue

        # ----------------------------------------------------
        # INT
        # ----------------------------------------------------
        m = INT_PATTERN.match(source, pos)
        if m:
            lex = m.group(0)
            start_col = column
            pos += len(lex)
            column += len(lex)
            yield Token(lex, line, start_col)
            continue

        # ----------------------------------------------------
        # Identificadores (incluyendo caracteres españoles)
        # ----------------------------------------------------
        if char.isalpha() or char == "_" or char >= "\u00C0":
            start = pos
            start_col = column
            pos += 1
            column += 1
            while pos < length:
                c = source[pos]
                if c.isalnum() or c == "_" or c >= "\u00C0":
                    pos += 1
                    column += 1
                else:
                    break
            lexeme = source[start:pos]
            yield Token(lexeme, line, start_col)
            continue

        # ----------------------------------------------------
        # Operadores de dos caracteres
        # ----------------------------------------------------
        two = source[pos:pos + 2]
        if two in ("==", "!=", "<=", ">=", "&&", "||"):
            yield Token(two, line, column)
            pos += 2
            column += 2
            continue

        # ----------------------------------------------------
        # Operadores de un carácter
        # ----------------------------------------------------
        if char in "+-*/%=(){};,<>!":
            yield Token(char, line, column)
            pos += 1
            column += 1
            continue

        # ----------------------------------------------------
        # Carácter inválido
        # ----------------------------------------------------
        error(f"Carácter inesperado: '{char}'")

    yield Token("EOF", line, column)

