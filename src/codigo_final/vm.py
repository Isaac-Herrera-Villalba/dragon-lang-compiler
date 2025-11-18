#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/codigo_final/vm.py
------------------------------------------------------------
Máquina virtual para Dragon-lang con:

- int, float, bool, string
- funciones con parámetros
- llamadas (param + call)
- recursión (pila de frames)
- return con o sin valor
- operadores aritméticos, lógicos y comparaciones
- concatenación de strings con +
------------------------------------------------------------
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from ..representacion_intermedia.ir import (
    IRProgram,
    Label, Goto, IfGoto,
    Assign, BinaryOp, UnaryOp,
    PrintInstr, ReadInstr,
    FuncLabel, ParamInstr, CallInstr,
    ReturnInstr, Instruction
)


class VMError(Exception):
    pass


@dataclass
class Frame:
    """
    Frame de ejecución de una función.
    """
    func_name: Optional[str]
    env: Dict[str, Any]
    return_ip: Optional[int]
    ret_dest: Optional[str]  # variable destino del valor de retorno en el llamador


class VirtualMachine:
    def __init__(self, program: IRProgram, func_param_names: Optional[Dict[str, List[str]]] = None):
        self.program = program
        self.instructions: List[Instruction] = program.instructions

        # etiquetas de saltos normales
        self.labels: Dict[str, int] = {}
        # inicio de funciones
        self.func_labels: Dict[str, int] = {}

        # firma de funciones: nombre → [param1, param2, ...]
        self.func_params: Dict[str, List[str]] = func_param_names or {}

        # pila de frames (llamadas)
        self.frames: List[Frame] = []

        # contexto actual
        self.current_func: Optional[str] = None
        self.env: Dict[str, Any] = {}
        self.ip: int = 0

        # pila de argumentos pendiente para la próxima llamada
        self.arg_stack: List[Any] = []

        # valor final (return de main)
        self.return_value: Any = None

        self._index_labels()

    # ============================================================
    #   Indexar etiquetas y funciones
    # ============================================================

    def _index_labels(self):
        for i, ins in enumerate(self.instructions):
            if isinstance(ins, Label):
                self.labels[ins.name] = i
            elif isinstance(ins, FuncLabel):
                # el nombre de la función es único
                self.func_labels[ins.name] = i

    # ============================================================
    #   Utilidades de valores
    # ============================================================

    def _get(self, operand: str) -> Any:
        """
        Interpreta operandos TAC:
        - literales: "3", "3.14", "true"/"false" → ya convertidos en IR a 1/0
        - string literal: "\"hola\""
        - nombre de variable / temporal: buscar en env
        """
        # literal string con comillas
        if operand.startswith('"') and operand.endswith('"'):
            return operand[1:-1]

        # variable/temporal
        if operand in self.env:
            return self.env[operand]

        # entero
        if operand.lstrip("-").isdigit():
            return int(operand)

        # float
        try:
            f = float(operand)
            # distinguir int vs float por la notación
            if "." in operand or "e" in operand.lower():
                return f
        except ValueError:
            pass

        # bool codificada como 0/1
        if operand == "0":
            return 0
        if operand == "1":
            return 1

        raise VMError(f"Uso de variable/temporal no inicializado: '{operand}'.")

    def _set(self, name: str, value: Any):
        self.env[name] = value

    # ============================================================
    #   Ejecución principal
    # ============================================================

    def run(self):
        # Buscar main
        if "main" not in self.func_labels:
            raise VMError("No se encontró la función 'main'.")

        # Simular una llamada inicial a main() sin caller
        self.current_func = "main"
        self.env = {}

        # ip al primer instr. DESPUÉS del FuncLabel de main
        self.ip = self.func_labels["main"] + 1

        while self.ip < len(self.instructions):
            ins = self.instructions[self.ip]

            # ----------------------------------------------------
            # Etiquetas y FuncLabel: no hacen nada en tiempo de ejecución
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

                # concatenación con strings
                if op == "+" and (isinstance(a, str) or isinstance(b, str)):
                    r = str(a) + str(b)
                    self._set(ins.dest, r)

                else:
                    # numéricos
                    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
                        raise VMError(f"Operador '{op}' requiere operandos numéricos (o string en '+').")

                    a_num = float(a)
                    b_num = float(b)

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

                    # guardar como int si es entero exacto
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
                # intentar interpretar como número
                try:
                    if "." in raw or "e" in raw.lower():
                        v = float(raw)
                    else:
                        v = int(raw)
                except Exception:
                    v = raw  # string si no es numérico
                self._set(ins.dest, v)

            # ----------------------------------------------------
            # Paso de parámetros
            # ----------------------------------------------------
            elif isinstance(ins, ParamInstr):
                val = self._get(ins.value)
                self.arg_stack.append(val)

            # ----------------------------------------------------
            # Llamada a función
            # ----------------------------------------------------
            elif isinstance(ins, CallInstr):
                callee = ins.callee
                arg_count = ins.arg_count

                if callee not in self.func_labels:
                    raise VMError(f"Función no encontrada: '{callee}'.")

                if arg_count > len(self.arg_stack):
                    raise VMError("Insuficientes argumentos en la pila de parámetros.")

                # Extraer los últimos arg_count argumentos
                args = self.arg_stack[-arg_count:]
                self.arg_stack = self.arg_stack[:-arg_count]

                # Obtener nombres de parámetros declarados
                param_names = self.func_params.get(callee, [])
                if len(param_names) != arg_count:
                    raise VMError(
                        f"Número de argumentos ({arg_count}) no coincide con "
                        f"parámetros declarados ({len(param_names)}) en '{callee}'."
                    )

                # Guardar frame actual
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
                # saltar al interior de la función
                self.ip = self.func_labels[callee] + 1
                continue

            # ----------------------------------------------------
            # return
            # ----------------------------------------------------
            elif isinstance(ins, ReturnInstr):
                # valor de retorno (si lo hay)
                rv = self._get(ins.value) if ins.value is not None else None

                if not self.frames:
                    # return desde main: terminar programa
                    self.return_value = rv
                    break

                # restaurar caller
                frame = self.frames.pop()

                # si el llamador espera destino, asignar allí el valor
                if frame.ret_dest is not None and rv is not None:
                    frame.env[frame.ret_dest] = rv

                self.env = frame.env
                self.current_func = frame.func_name
                self.ip = frame.return_ip
                continue

            else:
                raise VMError(f"Instrucción no soportada: {type(ins).__name__}")

            # avanzar
            self.ip += 1

        return self.return_value


# ============================================================
#   Función de conveniencia
# ============================================================

def run_ir_program(program: IRProgram, func_param_names: Optional[Dict[str, List[str]]] = None):
    """
    Ejecuta un IRProgram dado.

    func_param_names:
        diccionario opcional: nombre_función -> [lista de nombres de parámetros]

        Ejemplo:
            {
               "factorial": ["n"],
               "fib": ["x"],
               "main": []
            }
    """
    vm = VirtualMachine(program, func_param_names)
    return vm.run()

