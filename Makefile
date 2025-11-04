# Makefile para Dragon-lang

# Variables
PROJECT_NAME   = main
GRAMMAR_LEXER  = src/lexer/DragonLexer.g4
GRAMMAR_PARSER = grammar/DragonLang.g4
SRC_DIR        = src
TEST_SCRIPT    = $(SRC_DIR)/main.py

.PHONY: all help antlr run full clean

all: help

help:
	@echo "Opciones disponibles:"
	@echo "  make antlr     -> Genera lexer y parser desde las gramáticas (.g4)"
	@echo "  make run       -> Ejecuta el script principal $(TEST_SCRIPT)"
	@echo "  make full      -> Ejecuta antlr y luego run de $(TEST_SCRIPT)"
	@echo "  make clean     -> Elimina archivos generados por ANTLR y Python"

# Generar lexer y parser con ANTLR
antlr:
	@echo "Generando lexer y parser con ANTLR..."
	@echo "Generando lexer..."
	antlr4 -Dlanguage=Python3 -o $(SRC_DIR)/lexer $(GRAMMAR_LEXER)
	@echo "Generando parser..."
	antlr4 -Dlanguage=Python3 -o $(SRC_DIR)/parser -lib $(SRC_DIR)/lexer $(GRAMMAR_PARSER)

# Ejecutar script principal
run: $(TEST_SCRIPT)
	@echo "Ejecutando Dragon-lang..."
	python3 $(TEST_SCRIPT)

# Ejecutar todo el flujo: ANTLR + run
full: antlr run

# Limpiar archivos generados
clean:
	@echo "Eliminando archivos generados..."
	rm -fv $(SRC_DIR)/lexer/*Lexer*.py $(SRC_DIR)/parser/*Parser*.py
	rm -fv $(SRC_DIR)/lexer/*.tokens $(SRC_DIR)/parser/*.tokens
	rm -rfv $(SRC_DIR)/lexer/src/
	rm -rf $(SRC_DIR)/__pycache__

