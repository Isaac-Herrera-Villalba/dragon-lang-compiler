#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/analisis_semantico/symbol_table.py
------------------------------------------------------------
Descripción:
Módulo que implementa la tabla de símbolos para el compilador
Dragon-Lang.

Se encarga de:
- Representar símbolos (variables y funciones) con su tipo y metadatos.
- Gestionar scopes anidados (bloques, funciones, etc.).
- Resolver identificadores respetando la jerarquía de ámbitos.
- Mantener un scope global para las funciones y un scope actual
  para variables locales.

Este módulo es fundamental para el análisis semántico, ya que
permite verificar declaraciones, usos de variables y firmas de
funciones.
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
    """
    Representa una entrada en la tabla de símbolos.

    Atributos:
    - name: nombre del símbolo (variable o función).
    - kind: tipo de símbolo, "var" o "func".
    - type: para variables, su tipo estático (int/float/bool/string);
            para funciones, el tipo de retorno (string, o None inicial).
    - params: para funciones, lista de parámetros (normalmente ast.Param);
              para variables, None.
    """
    name: str
    kind: str             # "var" o "func"
    type: str             # para variables: int/float/bool/string
                          # para funciones: return type (string)
    params: Optional[List] = None   # lista de Param (para funciones)


# ============================================================
#   Excepción
# ============================================================

class SymbolTableError(Exception):
    """
    Excepción específica para errores relacionados con la
    tabla de símbolos, por ejemplo:
    - redeclaración de símbolos en el mismo scope
    - intentos de salir del scope global
    - acceso a funciones inexistentes al fijar metadatos
    """
    pass


# ============================================================
#   Scope
# ============================================================

class Scope:
    """
    Representa un ámbito (scope) en el programa.

    Cada scope:
    - Tiene un nombre descriptivo (por ejemplo, "global", "func main",
      "block", "for", etc.).
    - Mantiene un diccionario local de símbolos declarados en ese ámbito.
    - Tiene un puntero al scope padre, permitiendo la resolución
      jerárquica (búsqueda en scopes exteriores).
    """

    def __init__(self, name: str, parent: Optional["Scope"]) -> None:
        self.name = name
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}

    def define(self, symbol: Symbol) -> None:
        """
        Inserta un símbolo en el scope actual.

        Lanza SymbolTableError si el símbolo ya fue declarado en
        este mismo ámbito.
        """
        if symbol.name in self.symbols:
            raise SymbolTableError(
                f"Símbolo '{symbol.name}' ya declarado en scope '{self.name}'."
            )
        self.symbols[symbol.name] = symbol

    def resolve(self, name: str) -> Optional[Symbol]:
        """
        Busca un símbolo por nombre en este scope y, si no se
        encuentra, recurre al scope padre.

        Devuelve:
        - Symbol si se encuentra.
        - None si no existe en este scope ni en los padres.
        """
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
    Gestiona la pila de scopes y un scope global.

    Diseño:
    - global_scope: almacena símbolos globales, típicamente funciones.
    - current_scope: apunta al scope actual donde se declaran
      variables y se resuelven nombres.

    Ofrece operaciones para:
    - entrar y salir de scopes (push_scope / pop_scope)
    - declarar variables y funciones (define_var / define_func)
    - actualizar metadatos de funciones (tipo de retorno, parámetros)
    - resolver nombres tanto en el scope actual como en el global
    """

    def __init__(self) -> None:
        # Scope global donde se declaran las funciones
        self.global_scope = Scope("global", None)
        # Scope actual (empieza siendo el global)
        self.current_scope = self.global_scope

    # --------------------------------------------------------
    # Scopes
    # --------------------------------------------------------

    def push_scope(self, name: str) -> None:
        """
        Crea un nuevo scope hijo del scope actual y lo establece
        como scope activo.

        Ejemplos de nombres:
        - "func main"
        - "block"
        - "for"
        """
        new = Scope(name, self.current_scope)
        self.current_scope = new

    def pop_scope(self) -> None:
        """
        Sale del scope actual y regresa al scope padre.

        No permite salir del scope global (lanza SymbolTableError).
        """
        if self.current_scope.parent is None:
            raise SymbolTableError("No se puede salir del scope global.")
        self.current_scope = self.current_scope.parent

    # --------------------------------------------------------
    # Declaraciones de variables
    # --------------------------------------------------------

    def define_var(self, name: str, var_type: str) -> Symbol:
        """
        Declara una nueva variable en el scope actual.

        Parámetros:
        - name: nombre de la variable.
        - var_type: tipo estático ("int", "float", "bool", "string").

        Devuelve:
        - El objeto Symbol creado.

        Puede lanzar SymbolTableError si ya existe un símbolo con
        el mismo nombre en este scope.
        """
        symbol = Symbol(name=name, kind="var", type=var_type, params=None)
        self.current_scope.define(symbol)
        return symbol

    # --------------------------------------------------------
    # Declaraciones de funciones
    # --------------------------------------------------------

    def define_func(
        self,
        name: str,
        return_type: Optional[str],
        params: Optional[List] = None
    ) -> Symbol:
        """
        Declara una nueva función en el scope global.

        Parámetros:
        - name: nombre de la función.
        - return_type: tipo de retorno, usualmente None al inicio para
          indicar que el análisis semántico lo inferirá.
        - params: lista de parámetros (por ejemplo, nodos ast.Param).

        Devuelve:
        - El objeto Symbol creado.

        Puede lanzar SymbolTableError si una función con el mismo
        nombre ya ha sido declarada en el ámbito global.
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

    def set_func_return_type(self, name: str, return_type: str) -> None:
        """
        Fija el tipo de retorno de una función ya declarada
        en el scope global.

        Se consulta el símbolo con resolve_global y, si no existe
        o no es de tipo 'func', se lanza SymbolTableError.
        """
        func = self.resolve_global(name)
        if func is None or func.kind != "func":
            raise SymbolTableError(f"No existe función '{name}' para fijar return type.")
        func.type = return_type

    def set_func_params(self, name: str, params: List) -> None:
        """
        Fija la lista de parámetros de una función ya declarada.

        Parámetros:
        - name: nombre de la función.
        - params: lista de parámetros (por ejemplo, ast.Param).

        Lanza SymbolTableError si la función no existe o no es
        de tipo 'func'.
        """
        func = self.resolve_global(name)
        if func is None or func.kind != "func":
            raise SymbolTableError(f"No existe función '{name}' para fijar parámetros.")
        func.params = params

    # --------------------------------------------------------
    # Búsquedas
    # --------------------------------------------------------

    def resolve(self, name: str) -> Optional[Symbol]:
        """
        Resuelve un símbolo comenzando por el scope actual y
        ascendiendo por los scopes padres hasta el global.

        Equivale al uso normal de variables dentro de scopes
        anidados (sombreamiento de nombres, etc.).
        """
        return self.current_scope.resolve(name)

    def resolve_global(self, name: str) -> Optional[Symbol]:
        """
        Busca un símbolo únicamente en el scope global.

        Se utiliza principalmente para resolver funciones,
        ya que estas se registran en el ámbito global.
        """
        return self.global_scope.symbols.get(name)

