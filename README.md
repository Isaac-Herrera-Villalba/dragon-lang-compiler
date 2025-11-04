# 🐉 Dragon-Lang Compiler

## Descripción general

**Dragon-Lang** es un **lenguaje de programación experimental** y su respectivo **compilador** escrito completamente en **Python**.  
El propósito del proyecto es implementar, de forma didáctica, todas las fases del proceso de compilación, desde el **análisis léxico** hasta la **síntesis y optimización de código**, siguiendo la arquitectura clásica de un compilador.

El compilador procesa archivos fuente con extensión `.dragon`, generando una **representación intermedia** y posteriormente un **programa traducido** o ejecutable equivalente.

---

## 🧩 Componentes principales del compilador

El compilador se divide en **dos grandes fases**, según el modelo tradicional mostrado en el diagrama:

### 🔍 Fase 1: Análisis
Transforma el **programa fuente** en una **representación intermedia**.

- **Analizador Léxico (`lexer/`)**  
  Convierte la secuencia de caracteres del código fuente en una lista de *tokens*.
- **Analizador Sintáctico (`parser/`)**  
  Construye el árbol sintáctico a partir de los tokens, verificando la estructura del lenguaje.
- **Analizador Semántico (`semantic/`)**  
  Comprueba la coherencia de los tipos, variables y expresiones, generando tablas de símbolos.

📘 *Salida parcial:* Representación intermedia del programa y tablas semánticas.

---

### ⚙️ Fase 2: Síntesis
A partir de la representación intermedia, se construye el **programa traducido**.

- **Generador de Código (`codegen/`)**  
  Traduce la representación intermedia a código de destino (por ejemplo, Python, bytecode o ensamblador).
- **Optimizador de Código (`optimizer/`)**  
  Mejora el rendimiento del código generado mediante simplificaciones o transformaciones.

📗 *Salida final:* Código ejecutable o traducido.

---

