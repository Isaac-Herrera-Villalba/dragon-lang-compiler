#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/analisis_semantico/symbol_table.py
------------------------------------------------------------
Tabla de símbolos para Dragon-lang.

Soporta:
- funciones con parámetros
- return type (inferido por semantic.py)
- variables y scopes anidados
- búsqueda local y global
------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, List


# ============================================================
#   Símbolo
# ============================================================

@dataclass
class Symbol:
    name: str
    kind: str             # "var" o "func"
    type: str             # para variables: int/float/bool/string
                          # para funciones: return type (string)
    params: Optional[List] = None   # lista de Param (para funciones)


# ============================================================
#   Excepción
# ============================================================

class SymbolTableError(Exception):
    pass


# ============================================================
#   Scope
# ============================================================

class Scope:
    """
    Un scope contiene símbolos locales y un puntero al scope padre.
    """

    def __init__(self, name: str, parent: Optional["Scope"]) -> None:
        self.name = name
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}

    def define(self, symbol: Symbol):
        if symbol.name in self.symbols:
            raise SymbolTableError(
                f"Símbolo '{symbol.name}' ya declarado en scope '{self.name}'."
            )
        self.symbols[symbol.name] = symbol

    def resolve(self, name: str) -> Optional[Symbol]:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.resolve(name)
        return None


# ============================================================
#   Tabla de símbolos
# ============================================================

class SymbolTable:
    """
    Maneja una pila de scopes y un scope global para funciones.
    """

    def __init__(self) -> None:
        self.global_scope = Scope("global", None)
        self.current_scope = self.global_scope

    # --------------------------------------------------------
    # Scopes
    # --------------------------------------------------------

    def push_scope(self, name: str):
        new = Scope(name, self.current_scope)
        self.current_scope = new

    def pop_scope(self):
        if self.current_scope.parent is None:
            raise SymbolTableError("No se puede salir del scope global.")
        self.current_scope = self.current_scope.parent

    # --------------------------------------------------------
    # Declaraciones de variables
    # --------------------------------------------------------

    def define_var(self, name: str, var_type: str):
        symbol = Symbol(name=name, kind="var", type=var_type, params=None)
        self.current_scope.define(symbol)
        return symbol

    # --------------------------------------------------------
    # Declaraciones de funciones
    # --------------------------------------------------------

    def define_func(self, name: str, return_type: Optional[str], params: Optional[List] = None):
        """
        En nuestro modelo:
        - return_type inicialmente es None
        - params es lista de Param (ast.Param)
        """
        symbol = Symbol(
            name=name,
            kind="func",
            type=return_type,
            params=params if params else []
        )
        self.global_scope.define(symbol)
        return symbol

    # --------------------------------------------------------
    # Setters de metadatos de funciones
    # --------------------------------------------------------

    def set_func_return_type(self, name: str, return_type: str):
        func = self.resolve_global(name)
        if func is None or func.kind != "func":
            raise SymbolTableError(f"No existe función '{name}' para fijar return type.")
        func.type = return_type

    def set_func_params(self, name: str, params: List):
        func = self.resolve_global(name)
        if func is None or func.kind != "func":
            raise SymbolTableError(f"No existe función '{name}' para fijar parámetros.")
        func.params = params

    # --------------------------------------------------------
    # Búsquedas
    # --------------------------------------------------------

    def resolve(self, name: str) -> Optional[Symbol]:
        return self.current_scope.resolve(name)

    def resolve_global(self, name: str) -> Optional[Symbol]:
        return self.global_scope.symbols.get(name)

