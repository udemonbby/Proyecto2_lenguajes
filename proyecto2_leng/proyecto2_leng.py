import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import webbrowser
import os
from enum import Enum
from typing import List, Tuple
import re
import matplotlib.pyplot as plt

# Obtener el directorio del script
directorio_script = os.path.dirname(os.path.abspath(__file__))

class TipoToken(Enum):
    MENOR = "<"
    MAYOR = ">"
    BARRA = "/"
    IGUAL = "="
    IDENTIFICADOR = "Identifier"
    NUMERO = "Number"
    ERROR = "Error"

class Token:
    def __init__(self, tipo: TipoToken, lexema: str, fila: int, col: int):
        self.tipo = tipo
        self.lexema = lexema
        self.fila = fila
        self.col = col

    def __str__(self):
        return f"Token({self.tipo.value}, '{self.lexema}', fila {self.fila}:{self.col})"

class ReporteError:
    def __init__(self, lexema: str, fila: int, col: int):
        self.lexema = lexema
        self.fila = fila
        self.col = col

    def __str__(self):
        return f"ReporteError('{self.lexema}', fila {self.fila}:{self.col})"

class EscanerLexico:
    def __init__(self):
        self.tokens: List[Token] = []
        self.errores: List[ReporteError] = []

    def analizar_texto(self, text: str) -> Tuple[List[Token], List[ReporteError]]:
        lines = text.split('\n')
        fila = 1
        self.tokens = []
        self.errores = []
        for line in lines:
            col = 1
            i = 0
            while i < len(line):
                char = line[i]
                if char.isspace():
                    i += 1
                    col += 1
                    continue

                fila_inicio = fila
                col_inicio = col

                if char in "<>/=":
                    tipo = {
                        "<": TipoToken.MENOR,
                        ">": TipoToken.MAYOR,
                        "/": TipoToken.BARRA,
                        "=": TipoToken.IGUAL
                    }[char]
                    self.tokens.append(Token(tipo, char, fila_inicio, col_inicio))
                    i += 1
                    col += 1
                    continue

                if char.isalpha():
                    buffer = char
                    i += 1
                    col += 1
                    while i < len(line) and line[i].isalnum():
                        buffer += line[i]
                        i += 1
                        col += 1
                    self.tokens.append(Token(TipoToken.IDENTIFICADOR, buffer.upper(), fila_inicio, col_inicio))  # Normalizar a mayúsculas
                    continue

                if char.isdigit() or (char == '.' and i+1 < len(line) and line[i+1].isdigit()):
                    buffer = char
                    i += 1
                    col += 1
                    decimal = char == '.'
                    while i < len(line):
                        if line[i].isdigit():
                            buffer += line[i]
                            i += 1
                            col += 1
                        elif line[i] == '.' and not decimal:
                            buffer += '.'
                            i += 1
                            col += 1
                            decimal = True
                        else:
                            break
                    if re.match(r'^\d+(\.\d+)?$', buffer) or re.match(r'^\.\d+$', buffer):
                        self.tokens.append(Token(TipoToken.NUMERO, buffer, fila_inicio, col_inicio))
                    else:
                        self.errores.append(ReporteError(buffer, fila_inicio, col_inicio))
                    continue

                self.errores.append(ReporteError(char, fila_inicio, col_inicio))
                i += 1
                col += 1
            fila += 1
        return self.tokens, self.errores

class ErrorDeAnalisis(Exception):
    pass

class Nodo:
    pass

class Operacion(Nodo):
    def __init__(self, tipo_op: str, hijos: List[Nodo]):
        self.tipo_op = tipo_op
        self.hijos = hijos

    def etiqueta(self):
        return self.tipo_op

    def a_cadena(self):
        mapa_sim = {
            "SUMA": " + ",
            "RESTA": " - ",
            "MULTIPLICACION": " * ",
            "DIVISION": " / ",
            "POTENCIA": " ^ ",
            "RAIZ": "√",
            "INVERSO": "1/",
            "MOD": " % "
        }
        sim = mapa_sim[self.tipo_op]
        cadenas_hijos = []
        for h in self.hijos:
            s = h.a_cadena()
            if isinstance(h, Operacion):
                s = f"({s})"
            cadenas_hijos.append(s)
        if self.tipo_op == "RAIZ":
            if len(cadenas_hijos) == 1:
                return f"√{cadenas_hijos[0]}"
            else:
                return f"√[{cadenas_hijos[0]}]{cadenas_hijos[1]}"
        elif self.tipo_op == "INVERSO":
            return f"1/{cadenas_hijos[0]}"
        elif self.tipo_op == "POTENCIA":
            return "^".join(cadenas_hijos)
        return sim.join(cadenas_hijos)

class Numero(Nodo):
    def __init__(self, valor: str):
        self.valor = float(valor)

    def etiqueta(self):
        return str(self.valor)

    def a_cadena(self):
        return str(self.valor)

class AnalizadorSintactico:
    def __init__(self, tokens: List[Token], errores: List[ReporteError]):
        self.tokens = tokens
        self.errores = errores
        self.pos = 0
        self.ops_validas = ["SUMA", "RESTA", "MULTIPLICACION", "DIVISION", "POTENCIA", "RAIZ", "INVERSO", "MOD"]

    def analizar(self) -> List[Operacion]:
        operaciones = []
        while self.pos < len(self.tokens):
            try:
                op = self.analizar_operacion()
                operaciones.append(op)
            except ErrorDeAnalisis as e:
                # Saltar a la siguiente <Operacion o fin
                while self.pos < len(self.tokens) and not (self.tokens[self.pos].tipo == TipoToken.MENOR and self.pos + 1 < len(self.tokens) and self.tokens[self.pos+1].lexema == "OPERACION"):
                    self.pos += 1
        return operaciones

    def analizar_operacion(self) -> Operacion:
        self.esperar(TipoToken.MENOR)
        self.esperar_identificador("OPERACION")
        self.esperar(TipoToken.IGUAL)
        token_tipo_op = self.esperar(TipoToken.IDENTIFICADOR)
        tipo_op = token_tipo_op.lexema
        if tipo_op not in self.ops_validas:
            self.errores.append(ReporteError(tipo_op, token_tipo_op.fila, token_tipo_op.col))
            raise ErrorDeAnalisis(f"Tipo de operación inválido: {tipo_op}")
        self.esperar(TipoToken.MAYOR)
        hijos = []
        while not self.es_etiqueta_cierre("OPERACION"):
            if self.mirar(TipoToken.MENOR) and self.mirar_siguiente(TipoToken.IDENTIFICADOR, "NUMERO"):
                hijos.append(self.analizar_numero())
            elif self.mirar(TipoToken.MENOR) and self.mirar_siguiente(TipoToken.IDENTIFICADOR, "OPERACION"):
                hijos.append(self.analizar_operacion())
            else:
                encontrado = self.tokens[self.pos] if self.pos < len(self.tokens) else Token(TipoToken.ERROR, "EOF", 0, 0)
                self.errores.append(ReporteError(encontrado.lexema, encontrado.fila, encontrado.col))
                raise ErrorDeAnalisis("Esperado <Numero o <Operacion")
        self.esperar(TipoToken.MENOR)
        self.esperar(TipoToken.BARRA)
        self.esperar_identificador("OPERACION")
        self.esperar(TipoToken.MAYOR)
        return Operacion(tipo_op, hijos)

    def analizar_numero(self) -> Numero:
        self.esperar(TipoToken.MENOR)
        self.esperar_identificador("NUMERO")
        self.esperar(TipoToken.MAYOR)
        token_num = self.esperar(TipoToken.NUMERO)
        self.esperar(TipoToken.MENOR)
        self.esperar(TipoToken.BARRA)
        self.esperar_identificador("NUMERO")
        self.esperar(TipoToken.MAYOR)
        return Numero(token_num.lexema)

    def esperar(self, tipo: TipoToken) -> Token:
        if self.pos >= len(self.tokens) or self.tokens[self.pos].tipo != tipo:
            encontrado = self.tokens[self.pos] if self.pos < len(self.tokens) else Token(TipoToken.ERROR, "EOF", 0, 0)
            self.errores.append(ReporteError(encontrado.lexema, encontrado.fila, encontrado.col))
            raise ErrorDeAnalisis(f"Esperado {tipo.value}, encontrado {encontrado.lexema}")
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def esperar_identificador(self, esperado: str) -> Token:
        if self.pos >= len(self.tokens) or self.tokens[self.pos].tipo != TipoToken.IDENTIFICADOR or self.tokens[self.pos].lexema != esperado.upper():
            encontrado = self.tokens[self.pos] if self.pos < len(self.tokens) else Token(TipoToken.ERROR, "EOF", 0, 0)
            self.errores.append(ReporteError(encontrado.lexema, encontrado.fila, encontrado.col))
            raise ErrorDeAnalisis(f"Esperado identificador {esperado}, encontrado {encontrado.lexema}")
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def mirar(self, tipo: TipoToken) -> bool:
        return self.pos < len(self.tokens) and self.tokens[self.pos].tipo == tipo

    def mirar_siguiente(self, tipo: TipoToken, esperado: str) -> bool:
        return self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].tipo == tipo and self.tokens[self.pos + 1].lexema == esperado.upper()

    def es_etiqueta_cierre(self, etiqueta: str) -> bool:
        if self.pos + 3 >= len(self.tokens):
            return False
        return (self.tokens[self.pos].tipo == TipoToken.MENOR and
                self.tokens[self.pos + 1].tipo == TipoToken.BARRA and
                self.tokens[self.pos + 2].tipo == TipoToken.IDENTIFICADOR and self.tokens[self.pos + 2].lexema == etiqueta.upper() and
                self.tokens[self.pos + 3].tipo == TipoToken.MAYOR)

def evaluar(nodo: Nodo) -> float:
    if isinstance(nodo, Numero):
        return nodo.valor
    valores_hijos = [evaluar(hijo) for hijo in nodo.hijos]
    op = nodo.tipo_op
    if op == "SUMA":
        return sum(valores_hijos)
    elif op == "RESTA":
        res = valores_hijos[0]
        for v in valores_hijos[1:]:
            res -= v
        return res
    elif op == "MULTIPLICACION":
        res = 1
        for v in valores_hijos:
            res *= v
        return res
    elif op == "DIVISION":
        res = valores_hijos[0]
        for v in valores_hijos[1:]:
            res /= v
        return res
    elif op == "MOD":
        res = valores_hijos[0]
        for v in valores_hijos[1:]:
            res %= v
        return res
    elif op == "POTENCIA":
        res = valores_hijos[0]
        for v in valores_hijos[1:]:
            res **= v
        return res
    elif op == "RAIZ":
        # Asumiendo binario: índice raíz de base, o unario sqrt
        if len(valores_hijos) == 1:
            return valores_hijos[0] ** 0.5
        else:
            indice = valores_hijos[0]
            base = valores_hijos[1]
            return base ** (1 / indice)
    elif op == "INVERSO":
        return 1 / valores_hijos[0]
    raise ValueError(f"Operación desconocida: {op}")

def dibujar_arbol(nodo: Nodo, nombre_archivo: str):
    fig, ax = plt.subplots(figsize=(10, 10))
    def dibujar_nodo(n: Nodo, x: float, y: float, x_padre: float | None, y_padre: float | None):
        ax.text(x, y, n.etiqueta(), ha='center', va='center', bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.5'))
        if x_padre is not None:
            ax.plot([x_padre, x], [y_padre, y - 0.5], 'k-')  # Similar a flecha
        if isinstance(n, Operacion):
            num_hijos = len(n.hijos)
            extension = 3 * (num_hijos - 1) if num_hijos > 1 else 0
            for i, hijo in enumerate(n.hijos):
                x_hijo = x - extension / 2 + i * (extension / (num_hijos - 1) if num_hijos > 1 else 0)
                y_hijo = y - 3
                dibujar_nodo(hijo, x_hijo, y_hijo, x, y)
    dibujar_nodo(nodo, 0, 0, None, None)
    ax.set_xlim(-20, 20)
    ax.set_ylim(-20, 0)
    ax.axis('off')
    plt.savefig(os.path.join(directorio_script, nombre_archivo))
    plt.close()

class GUIdelAnalizador:
    def __init__(self, root):
        self.root = root
        self.root.title("Analizador de Operaciones Aritméticas")
        self.root.geometry("900x700")
        self.root.configure(bg="#f0f0f0")

        marco_superior = tk.Frame(root, bg="#4a90e2", height=50)
        marco_superior.pack(side=tk.TOP, fill=tk.X)
        marco_superior.pack_propagate(False)

        tk.Button(marco_superior, text="Abrir", command=self.abrir_archivo, bg="#ffffff", fg="#4a90e2", font=("Arial", 10, "bold"), relief="raised").pack(side=tk.LEFT, padx=10, pady=10)
        tk.Button(marco_superior, text="Guardar", command=self.guardar_archivo, bg="#ffffff", fg="#4a90e2", font=("Arial", 10, "bold"), relief="raised").pack(side=tk.LEFT, padx=5, pady=10)
        tk.Button(marco_superior, text="Guardar Como", command=self.guardar_como, bg="#ffffff", fg="#4a90e2", font=("Arial", 10, "bold"), relief="raised").pack(side=tk.LEFT, padx=5, pady=10)
        tk.Button(marco_superior, text="Analizar", command=self.analizar, bg="#ffffff", fg="#4a90e2", font=("Arial", 10, "bold"), relief="raised").pack(side=tk.LEFT, padx=10, pady=10)

        marco_central = tk.Frame(root, bg="#f0f0f0")
        marco_central.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(marco_central, text="Área de Texto", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(anchor="w")
        self.area_texto = scrolledtext.ScrolledText(marco_central, wrap=tk.WORD, width=60, height=35, font=("Arial", 10), relief="sunken", bd=2)
        self.area_texto.pack(fill=tk.BOTH, expand=True)

        marco_derecho = tk.Frame(root, bg="#e0e0e0", width=150)
        marco_derecho.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        marco_derecho.pack_propagate(False)

        tk.Label(marco_derecho, text="Opciones", font=("Arial", 12, "bold"), bg="#e0e0e0").pack(pady=10)
        tk.Button(marco_derecho, text="Manual de Usuario", command=self.abrir_manual_usuario, bg="#ffffff", fg="#4a90e2", font=("Arial", 9), relief="raised", width=15).pack(pady=5)
        tk.Button(marco_derecho, text="Manual Técnico", command=self.abrir_manual_tecnico, bg="#ffffff", fg="#4a90e2", font=("Arial", 9), relief="raised", width=15).pack(pady=5)
        tk.Button(marco_derecho, text="Ayuda", command=self.ayuda, bg="#ffffff", fg="#4a90e2", font=("Arial", 9), relief="raised", width=15).pack(pady=5)

    def abrir_archivo(self):
        nombre_archivo = filedialog.askopenfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if nombre_archivo:
            with open(nombre_archivo, 'r', encoding='utf-8') as f:
                self.area_texto.delete(1.0, tk.END)
                self.area_texto.insert(1.0, f.read())

    def guardar_archivo(self):
        nombre_archivo = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if nombre_archivo:
            with open(nombre_archivo, 'w', encoding='utf-8') as f:
                f.write(self.area_texto.get(1.0, tk.END))

    def guardar_como(self):
        self.guardar_archivo()

    def analizar(self):
        text = self.area_texto.get(1.0, tk.END)
        escaner = EscanerLexico()
        tokens, errors = escaner.analizar_texto(text)
        analizador = AnalizadorSintactico(tokens, errors)
        operaciones = analizador.analizar()
        errors = analizador.errores  # Actualizado con errores de análisis también

        ruta_errores = os.path.join(directorio_script, 'Errores.html')
        ruta_resultados = os.path.join(directorio_script, 'Resultados.html')

        # Siempre intentar generar Resultados.html si hay operaciones, incluso si hay errores
        if operaciones:
            with open(ruta_resultados, 'w', encoding='utf-8') as f:
                f.write("<html><head><meta charset='UTF-8'></head><body><h1>Resultados</h1>")
                contadores_simples = {op: 0 for op in analizador.ops_validas}
                contador_complejo = 0
                for i, op in enumerate(operaciones, 1):
                    es_complejo = any(isinstance(hijo, Operacion) for hijo in op.hijos)
                    if es_complejo:
                        contador_complejo += 1
                        titulo = f"Operación Compleja {contador_complejo}"
                    else:
                        contadores_simples[op.tipo_op] += 1
                        titulo = f"Operación {op.tipo_op} {contadores_simples[op.tipo_op]}"
                    expr = op.a_cadena()
                    try:
                        resultado = evaluar(op)
                    except Exception as e:
                        resultado = f"Error en evaluación: {str(e)}"
                    archivo_imagen = f"arbol_{i}.png"
                    dibujar_arbol(op, archivo_imagen)
                    f.write(f"<h2>{titulo}</h2><p>{expr} = {resultado}</p><img src='{archivo_imagen}' alt='Árbol de expresión {i}'><br><br>")
                f.write("</body></html>")
            webbrowser.open(ruta_resultados)

        # Generar Errores.html si hay errores
        if errors:
            with open(ruta_errores, 'w', encoding='utf-8') as f:
                f.write("<html><head><meta charset='UTF-8'></head><body><h1>Reporte de Errores</h1><table border='1' style='border-collapse: collapse;'><tr><th>No.</th><th>Lexema</th><th>Tipo</th><th>Columna</th><th>Fila</th></tr>")
                for i, err in enumerate(errors, 1):
                    f.write(f"<tr><td>{i}</td><td>{err.lexema}</td><td>Error</td><td>{err.col}</td><td>{err.fila}</td></tr>")
                f.write("</table></body></html>")
            webbrowser.open(ruta_errores)

        messagebox.showinfo("Análisis Completado", f"Tokens: {len(tokens)}, Errores: {len(errors)}. Archivos generados en {directorio_script}.")

    def abrir_manual_usuario(self):
        ruta_manual = os.path.join(directorio_script, "ManualUsuario.pdf")
        if os.path.exists(ruta_manual):
            os.startfile(ruta_manual)
        else:
            messagebox.showerror("Error", "ManualUsuario.pdf no encontrado. Crea el archivo.")

    def abrir_manual_tecnico(self):
        ruta_manual = os.path.join(directorio_script, "ManualTecnico.pdf")
        if os.path.exists(ruta_manual):
            os.startfile(ruta_manual)
        else:
            messagebox.showerror("Error", "ManualTecnico.pdf no encontrado. Crea el archivo.")

    def ayuda(self):
        messagebox.showinfo("Ayuda", "Analizador de Operaciones Aritméticas\nDesarrollador: Brandon Salazar - José Daniel Paz\nCarnets: 1111322 / 1200022\nGuatemala, 22 de octubre 2025")

if __name__ == "__main__":
    root = tk.Tk()
    app = GUIdelAnalizador(root)
    root.mainloop()