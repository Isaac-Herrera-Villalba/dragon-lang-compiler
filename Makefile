# ============================================================
# Makefile para el compilador Dragon-lang
# ============================================================

PYTHON       = python3
SRC_DIR      = src
MAIN_MODULE  = main
EXAMPLES_DIR = examples
EXAMPLES     = $(wildcard $(EXAMPLES_DIR)/*.dragon)

.PHONY: help run  all-examples clean

# ------------------------------------------------------------
# Ayuda
# ------------------------------------------------------------
help:
	@echo "=============================================="
	@echo "     Opciones disponibles (Dragon-lang)        "
	@echo "=============================================="
	@echo ""
	@echo "  make run <archivo>        Ejecuta un .dragon"
	@echo "     Ejemplos:"
	@echo "       make run ejemplo0"
	@echo "       make run ejemplo0.dragon"
	@echo ""
	@echo "  make all-examples        Ejecuta todos los .dragon"
	@echo ""
	@echo "  make clean                Limpia __pycache__"
	@echo ""

# ------------------------------------------------------------
# Ejecutar archivos .dragon sin escribir FILE=
# ------------------------------------------------------------
run:
	@if [ -z "$(word 2,$(MAKECMDGOALS))" ]; then \
		echo "Uso: make run <archivo.dragon>"; \
		exit 1; \
	fi; \
	FILE=$(word 2,$(MAKECMDGOALS)); \
	case $$FILE in \
		*.dragon) TARGET="$$FILE" ;; \
		*) TARGET="$$FILE.dragon" ;; \
	esac; \
	if [ ! -f "$(EXAMPLES_DIR)/$$TARGET" ]; then \
		echo "Error: El archivo '$(EXAMPLES_DIR)/$$TARGET' no existe."; \
		exit 1; \
	fi; \
	$(PYTHON) -m $(SRC_DIR).$(MAIN_MODULE) $(EXAMPLES_DIR)/$$TARGET

# ------------------------------------------------------------
# Ejecutar TODOS los archivos .dragon detectados allmáticamente
# ------------------------------------------------------------
all-examples:
	@echo "Ejecutando TODOS los archivos .dragon detectados:"
	@for f in $(EXAMPLES); do \
		echo "---------------------------------------"; \
		echo "Ejecutando $$f"; \
		$(PYTHON) -m $(SRC_DIR).$(MAIN_MODULE) $$f; \
		echo ""; \
	done
	@echo "---------------------------------------"
	@echo "Fin de ejecución automática."

# ------------------------------------------------------------
# Limpieza
# ------------------------------------------------------------
clean:
	find $(SRC_DIR) -type d -name "__pycache__" -exec rm -rf {} +
	find $(SRC_DIR) -type f -name "*.pyc" -delete
	@echo "Limpieza completa."

# ------------------------------------------------------------
# Evitar que make intente crear archivos con nombres de ejemplo
# ------------------------------------------------------------
%:
	@:

