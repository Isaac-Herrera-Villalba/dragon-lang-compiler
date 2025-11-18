#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/codigo_final/vm.py
------------------------------------------------------------
Descripción:
Implementa la máquina virtual (VM) para ejecutar el código
intermedio (IR/TAC) generado por el compilador de Dragon-Lang.

La VM:
- Interpreta instrucciones TAC (asignaciones, operaciones, saltos).
- Gestiona una pila de frames para soportar funciones y recursión.
- Implementa paso de parámetros y retorno de valores.
- Maneja tipos básicos: int, float, bool (como 0/1) y string.
- Soporta I/O mediante instrucciones print y read.

Esta es la fase final del pipeline: ejecuta el programa optimizado.
------------------------------------------------------------
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from ..representacion_intermedia.ir import (
    IRProgram,
    Label,
    Goto,
    IfGoto,
    Assign,
    BinaryOp,
    UnaryOp,
    PrintInstr,
    ReadInstr,
    FuncLabel,
    ParamInstr,
    CallInstr,
    ReturnInstr,
    Instruction
)


class VMError(Exception):
    """
    Excepción específica para errores de ejecución en la
    máquina virtual, tales como:
    - División entre cero
    - Uso de variables no inicializadas
    - Funciones o etiquetas inexistentes
    - Inconsistencias en llamadas y retornos
    """
    pass


@dataclass
class Frame:
    """
    Frame de ejecución de una función en la pila de llamadas.

    Atributos:
    - func_name: nombre de la función actual (None para main inicial
      si se considera como "nivel raíz").
    - env: entorno de variables locales (diccionario nombre → valor).
    - return_ip: posición en la lista de instrucciones a la que se
      debe regresar tras el return.
    - ret_dest: nombre de la variable/temporal en el llamador donde
      debe almacenarse el valor de retorno, o None si se ignora.
    """
    func_name: Optional[str]
    env: Dict[str, Any]
    return_ip: Optional[int]
    ret_dest: Optional[str]


class VirtualMachine:
    """
    Máquina virtual para ejecutar programas en IR/TAC.

    Funciona como un intérprete de instrucciones lineales con:
    - Pila de frames para llamadas a funciones.
    - Entorno de variables por función.
    - Mapa de etiquetas y funciones a índices de instrucciones.
    """

    def __init__(self, program: IRProgram, func_param_names: Optional[Dict[str, List[str]]] = None):
        # Programa IR
        self.program = program
        self.instructions: List[Instruction] = program.instructions

        # Mapas de etiquetas y funciones a índices de instrucción
        self.labels: Dict[str, int] = {}
        self.func_labels: Dict[str, int] = {}

        # Firma de funciones: nombre → lista de nombres de parámetros
        self.func_params: Dict[str, List[str]] = func_param_names or {}

        # Pila de frames (para llamadas anidadas / recursión)
        self.frames: List[Frame] = []

        # Contexto actual de ejecución
        self.current_func: Optional[str] = None
        self.env: Dict[str, Any] = {}
        self.ip: int = 0  # Instruction Pointer

        # Pila de argumentos pendiente para la siguiente llamada
        self.arg_stack: List[Any] = []

        # Valor final de retorno (return desde main)
        self.return_value: Any = None

        # Indexar etiquetas y funciones
        self._index_labels()

    # ============================================================
    #   Indexación de etiquetas y funciones
    # ============================================================

    def _index_labels(self) -> None:
        """
        Recorre las instrucciones del IR para construir:
        - labels: nombre_etiqueta → índice de instrucción
        - func_labels: nombre_función → índice donde inicia su cuerpo
        """
        for i, ins in enumerate(self.instructions):
            if isinstance(ins, Label):
                self.labels[ins.name] = i
            elif isinstance(ins, FuncLabel):
                self.func_labels[ins.name] = i

    # ============================================================
    #   Utilidades de acceso a valores
    # ============================================================

    def _get(self, operand: str) -> Any:
        """
        Obtiene el valor asociado a un operando TAC.

        Reglas:
        - Si es una cadena entre comillas: se devuelve el contenido.
        - Si es el nombre de una variable/temporal: se busca en env.
        - Si es un literal numérico entero o flotante: se convierte.
        - Si es "0" o "1": se interpreta como entero (para bool).
        - Si no cae en ninguno de los casos y no está en env:
          se considera error de variable no inicializada.
        """
        # String literal con comillas
        if operand.startswith('"') and operand.endswith('"'):
            return operand[1:-1]

        # Variable/temporal
        if operand in self.env:
            return self.env[operand]

        # Entero (soporta signo)
        if operand.lstrip("-").isdigit():
            return int(operand)

        # Float
        try:
            f = float(operand)
            # Determina si se mantiene como float según el formato
            if "." in operand or "e" in operand.lower():
                return f
        except ValueError:
            pass

        # Booleanos codificados como 0/1
        if operand == "0":
            return 0
        if operand == "1":
            return 1

        raise VMError(f"Uso de variable/temporal no inicializado: '{operand}'.")

    def _set(self, name: str, value: Any) -> None:
        """
        Asigna un valor a una variable/temporal en el entorno actual.
        """
        self.env[name] = value

    # ============================================================
    #   Bucle principal de ejecución
    # ============================================================

    def run(self):
        """
        Ejecuta el programa IR.

        Pasos:
        - Busca la función 'main'.
        - Simula una llamada inicial a main() sin llamador.
        - Ejecuta instrucciones hasta que:
          - se hace return en main
          - o se llega al final del programa.
        """
        # Verificar que exista main
        if "main" not in self.func_labels:
            raise VMError("No se encontró la función 'main'.")

        # Inicializar contexto para 'main'
        self.current_func = "main"
        self.env = {}

        # Colocar IP en la instrucción siguiente a FuncLabel main
        self.ip = self.func_labels["main"] + 1

        # Bucle principal de ejecución
        while self.ip < len(self.instructions):
            ins = self.instructions[self.ip]

            # ----------------------------------------------------
            # Etiquetas y FuncLabel (no ejecutables)
            # ----------------------------------------------------
            if isinstance(ins, (Label, FuncLabel)):
                self.ip += 1
                continue

            # ----------------------------------------------------
            # Asignación simple
            # ----------------------------------------------------
            if isinstance(ins, Assign):
                val = self._get(ins.src)
                self._set(ins.dest, val)

            # ----------------------------------------------------
            # Operación binaria
            # ----------------------------------------------------
            elif isinstance(ins, BinaryOp):
                a = self._get(ins.left)
                b = self._get(ins.right)
                op = ins.op

                # Concatenación con strings
                if op == "+" and (isinstance(a, str) or isinstance(b, str)):
                    r = str(a) + str(b)
                    self._set(ins.dest, r)

                else:
                    # Validación numérica
                    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
                        raise VMError(f"Operador '{op}' requiere operandos numéricos (o string en '+').")

                    a_num = float(a)
                    b_num = float(b)

                    # Operadores aritméticos / comparaciones / lógicos
                    if op == "+":
                        r = a_num + b_num
                    elif op == "-":
                        r = a_num - b_num
                    elif op == "*":
                        r = a_num * b_num
                    elif op == "/":
                        if b_num == 0:
                            raise VMError("División entre cero.")
                        r = a_num / b_num
                    elif op == "%":
                        if not isinstance(a, int) or not isinstance(b, int):
                            raise VMError("El operador '%' solo está definido para enteros.")
                        r = a % b
                    elif op == "<":
                        r = int(a_num < b_num)
                    elif op == "<=":
                        r = int(a_num <= b_num)
                    elif op == ">":
                        r = int(a_num > b_num)
                    elif op == ">=":
                        r = int(a_num >= b_num)
                    elif op == "==":
                        r = int(a_num == b_num)
                    elif op == "!=":
                        r = int(a_num != b_num)
                    elif op == "&&":
                        r = int(bool(a_num) and bool(b_num))
                    elif op == "||":
                        r = int(bool(a_num) or bool(b_num))
                    else:
                        raise VMError(f"Operador binario no soportado: '{op}'.")

                    # Guardar como int si el resultado flotante es entero exacto
                    if isinstance(r, float) and r.is_integer():
                        r = int(r)
                    self._set(ins.dest, r)

            # ----------------------------------------------------
            # Operación unaria
            # ----------------------------------------------------
            elif isinstance(ins, UnaryOp):
                a = self._get(ins.operand)
                op = ins.op

                if op == "-":
                    if not isinstance(a, (int, float)):
                        raise VMError("El operador '-' requiere operando numérico.")
                    r = -a
                elif op == "!":
                    r = 0 if a else 1
                else:
                    raise VMError(f"Operador unario no soportado: '{op}'.")
                self._set(ins.dest, r)

            # ----------------------------------------------------
            # Saltos
            # ----------------------------------------------------
            elif isinstance(ins, Goto):
                if ins.target not in self.labels:
                    raise VMError(f"Etiqueta desconocida: '{ins.target}'.")
                self.ip = self.labels[ins.target]
                continue

            elif isinstance(ins, IfGoto):
                cond = self._get(ins.condition)
                if cond != 0:
                    if ins.target not in self.labels:
                        raise VMError(f"Etiqueta desconocida: '{ins.target}'.")
                    self.ip = self.labels[ins.target]
                    continue

            # ----------------------------------------------------
            # I/O
            # ----------------------------------------------------
            elif isinstance(ins, PrintInstr):
                val = self._get(ins.value)
                print(val)

            elif isinstance(ins, ReadInstr):
                raw = input().strip()
                # Intentar interpretar como número
                try:
                    if "." in raw or "e" in raw.lower():
                        v = float(raw)
                    else:
                        v = int(raw)
                except Exception:
                    # Si no es numérico, se conserva como cadena
                    v = raw
                self._set(ins.dest, v)

            # ----------------------------------------------------
            # Paso de parámetros
            # ----------------------------------------------------
            elif isinstance(ins, ParamInstr):
                val = self._get(ins.value)
                self.arg_stack.append(val)

            # ----------------------------------------------------
            # Llamadas a función
            # ----------------------------------------------------
            elif isinstance(ins, CallInstr):
                callee = ins.callee
                arg_count = ins.arg_count

                if callee not in self.func_labels:
                    raise VMError(f"Función no encontrada: '{callee}'.")

                if arg_count > len(self.arg_stack):
                    raise VMError("Insuficientes argumentos en la pila de parámetros.")

                # Extraer últimos arg_count argumentos
                args = self.arg_stack[-arg_count:]
                self.arg_stack = self.arg_stack[:-arg_count]

                # Nombres de parámetros declarados
                param_names = self.func_params.get(callee, [])
                if len(param_names) != arg_count:
                    raise VMError(
                        f"Número de argumentos ({arg_count}) no coincide con "
                        f"parámetros declarados ({len(param_names)}) en '{callee}'."
                    )

                # Guardar frame actual (caller)
                frame = Frame(
                    func_name=self.current_func,
                    env=self.env,
                    return_ip=self.ip + 1,
                    ret_dest=ins.dest
                )
                self.frames.append(frame)

                # Crear nuevo entorno para la función llamada
                new_env: Dict[str, Any] = {}
                for name, val in zip(param_names, args):
                    new_env[name] = val

                self.env = new_env
                self.current_func = callee
                self.ip = self.func_labels[callee] + 1
                continue

            # ----------------------------------------------------
            # return
            # ----------------------------------------------------
            elif isinstance(ins, ReturnInstr):
                # Valor de retorno si existe
                rv = self._get(ins.value) if ins.value is not None else None

                # Si no hay frames, es un return desde main → fin
                if not self.frames:
                    self.return_value = rv
                    break

                # Restaurar contexto del llamador
                frame = self.frames.pop()

                # Asignar valor de retorno en el llamador si corresponde
                if frame.ret_dest is not None and rv is not None:
                    frame.env[frame.ret_dest] = rv

                self.env = frame.env
                self.current_func = frame.func_name
                self.ip = frame.return_ip
                continue

            else:
                raise VMError(f"Instrucción no soportada: {type(ins).__name__}")

            # Avanzar a la siguiente instrucción por defecto
            self.ip += 1

        return self.return_value


# ============================================================
#   Función de conveniencia
# ============================================================

def run_ir_program(program: IRProgram, func_param_names: Optional[Dict[str, List[str]]] = None):
    """
    Ejecuta un IRProgram en una máquina virtual nueva.

    Parámetros:
    - program: objeto IRProgram con la lista de instrucciones TAC.
    - func_param_names: diccionario opcional que mapea el nombre
      de la función a la lista de nombres de sus parámetros.

    Devuelve:
    - El valor de retorno de la función main, si lo hay.
    """
    vm = VirtualMachine(program, func_param_names)
    return vm.run()

