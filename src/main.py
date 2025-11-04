#!/usr/bin/env python3

from antlr4 import *
from src.lexer.DragonLexer import DragonLexer

# Cadena de prueba
input_text = "x + 23 * y"

# Crear flujo de caracteres
input_stream = InputStream(input_text)

# Crear lexer
lexer = DragonLexer(input_stream)

# Mostrar tokens
for token in lexer.getAllTokens():
    print(f"{token.text} -> {lexer.symbolicNames[token.type]}")

