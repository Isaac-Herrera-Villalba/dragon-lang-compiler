# Dragon-Lang Compiler

## Descripción general
Dragon-Lang es un lenguaje de programación experimental y un compilador escrito en Python.  
Implementa todas las fases clásicas de un compilador: análisis léxico, análisis sintáctico, análisis semántico, generación de representación intermedia (TAC), optimización y ejecución mediante una máquina virtual con pila de llamadas.

El compilador procesa archivos `.dragon`, genera IR optimizado y ejecuta el programa resultante.

## Características del lenguaje
- Tipos: `int`, `float`, `bool`, `string`
- Declaración de variables y expresiones aritméticas, lógicas y comparaciones
- Control de flujo: `if`, `else`, `while`, `do-while`, `for`
- Entrada y salida: `print`, `read`
- Funciones con parámetros, llamadas y recursión
- Concatenación de cadenas con `+`

## Pipeline del compilador
1. Tokenización  
2. Parser descendente recursivo (AST)  
3. Análisis semántico con tabla de símbolos  
4. Generación de IR (Three-Address Code)  
5. Optimización del IR  
6. Ejecución en una máquina virtual propia

## Uso
Ejecutar un archivo `.dragon`:

```bash
 make run <archivo>.dragon
```


Ejecutar todos los archivos `.dragon`:

```bash
 make all-examples
```

