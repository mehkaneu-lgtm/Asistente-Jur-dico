"""
Plantilla de interfaz de escritorio para IA (estilo Claude / Copilot)
con panel lateral desplegable para seleccionar y abrir PDFs de Jurisprudencia.
"""

import os
import textwrap
import threading
import time
import uuid
import subprocess
import platform
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox

# Pillow es opcional: si está instalado, permite cargar logos en más
# formatos (JPG, etc.) y redimensionarlos con buena calidad. Si no está
# instalado, se usa tk.PhotoImage (soporta PNG/GIF/PPM de forma nativa).
try:
    from PIL import Image, ImageTk
    _PIL_DISPONIBLE = True
except ImportError:
    _PIL_DISPONIBLE = False

# ----------------------------------------------------------------------
# PALETAS DE COLORES
# (estilo Portal de Servicios en Línea del Poder Judicial de la
# Federación: guinda institucional, dorado y fondo claro, con
# equivalente en modo oscuro)
# ----------------------------------------------------------------------
PALETA_CLARA = {
    "BG_SIDEBAR": "#F2ECDF",       # beige claro institucional
    "BG_MAIN": "#FFFFFF",          # blanco
    "BG_INPUT": "#FFFFFF",
    "BG_BUBBLE_USER": "#F6E6EA",   # tinte guinda muy claro
    "BG_BUBBLE_IA": "#FFFFFF",
    "TEXT_PRIMARY": "#2B2B2B",
    "TEXT_SECONDARY": "#756B57",
    "ACCENT": "#9F2241",           # guinda institucional (Gobierno de México)
    "ACCENT_HOVER": "#7A1B33",
    "BORDER": "#D8CFB8",           # línea dorada/beige sutil
    "SCROLLBAR": "#C9BFA4",
}

PALETA_OSCURA = {
    "BG_SIDEBAR": "#201A17",
    "BG_MAIN": "#171310",
    "BG_INPUT": "#2A231F",
    "BG_BUBBLE_USER": "#3A2229",
    "BG_BUBBLE_IA": "#2A231F",
    "TEXT_PRIMARY": "#EFE9E1",
    "TEXT_SECONDARY": "#B8A98F",
    "ACCENT": "#D9648A",           # guinda más claro para contraste en oscuro
    "ACCENT_HOVER": "#C24A72",
    "BORDER": "#4A3F35",
    "SCROLLBAR": "#4A3F35",
}

FONT_FAMILY = "Segoe UI"

# La carpeta se crea SIEMPRE junto a este archivo .py, sin importar desde
# dónde se ejecute el script (doble clic, terminal, acceso directo, etc.)
CARPETA_PDFS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jurisprudencias_pdf")

# ----------------------------------------------------------------------
# LOGO (esquina superior izquierda del panel lateral)
# ----------------------------------------------------------------------
# Para agregar tu logo, simplemente coloca un archivo llamado "logo.png"
# (o .jpg/.jpeg/.gif si tienes Pillow instalado) en la misma carpeta que
# este script. Se detectará y cargará automáticamente al iniciar la app.
# Si no encuentra el archivo, se muestra un espacio reservado con el
# nombre de archivo esperado, sin romper la aplicación.
CARPETA_APP = os.path.dirname(os.path.abspath(__file__))
NOMBRES_LOGO_POSIBLES = ["logo.png", "logo.jpg", "logo.jpeg", "logo.gif"]
LOGO_ANCHO_MAX = 170   # ancho máximo en píxeles dentro del sidebar (260px)
LOGO_ALTO_MAX = 100     # alto máximo en píxeles


class Mensaje:
    def __init__(self, autor, texto):
        self.autor = autor  # "user" o "ia"
        self.texto = texto


class Conversacion:
    def __init__(self, titulo="Nuevo caso"):
        self.id = str(uuid.uuid4())
        self.titulo = titulo
        self.mensajes = []


class IAApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Asesor Jurídico")
        self.geometry("1100x720")
        self.minsize(760, 480)

        # Tema (claro/oscuro)
        self.modo_oscuro = False
        self.colors = dict(PALETA_CLARA)

        self.configure(bg=self.colors["BG_MAIN"])

        # Fuentes
        self.font_normal = tkfont.Font(family=FONT_FAMILY, size=11)
        self.font_bold = tkfont.Font(family=FONT_FAMILY, size=11, weight="bold")
        self.font_small = tkfont.Font(family=FONT_FAMILY, size=9)
        self.font_titulo = tkfont.Font(family=FONT_FAMILY, size=13, weight="bold")

        # Estado
        self.conversaciones = {}
        self.conversacion_actual = None
        self.generando = False

        # Estado del panel de Jurisprudencia
        self.panel_pdf_visible = False

        # Asegurar que la carpeta de PDFs exista (junto al script)
        try:
            if not os.path.exists(CARPETA_PDFS):
                os.makedirs(CARPETA_PDFS)
                print(f"[Jurisprudencia] Carpeta creada en: {CARPETA_PDFS}")
            else:
                print(f"[Jurisprudencia] Usando carpeta existente: {CARPETA_PDFS}")
        except OSError as e:
            print(f"[Jurisprudencia] No se pudo crear la carpeta '{CARPETA_PDFS}': {e}")

        self._construir_layout()
        self.nueva_conversacion()

    # ------------------------------------------------------------------
    # LAYOUT PRINCIPAL
    # ------------------------------------------------------------------
    def _construir_layout(self):
        contenedor = tk.Frame(self, bg=self.colors["BG_MAIN"])
        contenedor.pack(fill="both", expand=True)

        self._construir_sidebar(contenedor)
        self._construir_panel_pdf(contenedor)  # Panel desplegable (oculto al inicio)
        self._construir_panel_chat(contenedor)

    # ------------------------------------------------------------------
    # BARRA LATERAL (IZQUIERDA)
    # ------------------------------------------------------------------
    def _construir_sidebar(self, parent):
        self.sidebar = tk.Frame(parent, bg=self.colors["BG_SIDEBAR"], width=260)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo (arriba a la izquierda del sidebar)
        self.frame_logo = tk.Frame(self.sidebar, bg=self.colors["BG_SIDEBAR"])
        self.frame_logo.pack(fill="x", padx=14, pady=(16, 0))
        self._cargar_logo(self.frame_logo)

        # Botón "Nuevo chat"
        btn_nuevo = tk.Button(
            self.sidebar,
            text="+  Nuevo caso",
            font=self.font_bold,
            bg=self.colors["ACCENT"],
            fg="white",
            activebackground=self.colors["ACCENT_HOVER"],
            activeforeground="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            anchor="w",
            padx=14,
            pady=10,
            command=self.nueva_conversacion,
        )
        btn_nuevo.pack(fill="x", padx=14, pady=(16, 10))

        # ------------------------------------------------------------
        # Accesos rápidos (iconos de funcionalidades)
        # ------------------------------------------------------------
        frame_accesos = tk.Frame(self.sidebar, bg=self.colors["BG_SIDEBAR"])
        frame_accesos.pack(fill="x", padx=8, pady=(4, 12))

        self._crear_item_nav(frame_accesos, "⚖", "Jurisprudencia", self.abrir_jurisprudencia)
        self._crear_item_nav(frame_accesos, "📜", "Sentencias", self.abrir_sentencias)

        # Separador sutil entre accesos rápidos e historial
        separador = tk.Frame(self.sidebar, bg=self.colors["BORDER"], height=1)
        separador.pack(fill="x", padx=16, pady=(0, 8))

        # Etiqueta "Historial"
        lbl_hist = tk.Label(
            self.sidebar,
            text="HISTORIAL",
            font=self.font_small,
            bg=self.colors["BG_SIDEBAR"],
            fg=self.colors["TEXT_SECONDARY"],
            anchor="w",
        )
        lbl_hist.pack(fill="x", padx=16, pady=(10, 4))

        # Lista de conversaciones (scrollable)
        self.frame_historial = tk.Frame(self.sidebar, bg=self.colors["BG_SIDEBAR"])
        self.frame_historial.pack(fill="both", expand=True, padx=8)

        # Footer sidebar (botón de modo oscuro / claro)
        footer = tk.Frame(self.sidebar, bg=self.colors["BG_SIDEBAR"], height=54)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        self.btn_tema = tk.Button(
            footer,
            text=self._texto_boton_tema(),
            font=self.font_normal,
            bg=self.colors["BG_SIDEBAR"],
            fg=self.colors["TEXT_SECONDARY"],
            activebackground=self.colors["BG_INPUT"],
            activeforeground=self.colors["TEXT_PRIMARY"],
            relief="flat",
            bd=0,
            anchor="w",
            padx=16,
            pady=14,
            cursor="hand2",
            command=self.alternar_tema,
        )
        self.btn_tema.pack(fill="x")

    # ------------------------------------------------------------------
    # LOGO
    # ------------------------------------------------------------------
    def _buscar_ruta_logo(self):
        """Devuelve la ruta del primer archivo de logo encontrado junto
        al script, o None si no hay ninguno."""
        for nombre in NOMBRES_LOGO_POSIBLES:
            ruta = os.path.join(CARPETA_APP, nombre)
            if os.path.exists(ruta):
                return ruta
        return None

    def _cargar_logo(self, parent):
        """Carga y muestra el logo en 'parent'. Si no encuentra el
        archivo, o si falla la carga, simplemente no muestra nada."""
        ruta_logo = self._buscar_ruta_logo()
        if not ruta_logo:
            return

        try:
            if _PIL_DISPONIBLE:
                imagen = Image.open(ruta_logo)
                # Redimensiona conservando proporción para caber en el sidebar
                imagen.thumbnail((LOGO_ANCHO_MAX, LOGO_ALTO_MAX), Image.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(imagen)
            else:
                # Sin Pillow: tk.PhotoImage soporta PNG/GIF nativamente
                # (pero no redimensiona con buena calidad, solo por subsampleo)
                img = tk.PhotoImage(file=ruta_logo)
                factor_x = max(1, img.width() // LOGO_ANCHO_MAX)
                factor_y = max(1, img.height() // LOGO_ALTO_MAX)
                factor = max(factor_x, factor_y)
                if factor > 1:
                    img = img.subsample(factor, factor)
                self.logo_img = img

            lbl_logo = tk.Label(
                parent,
                image=self.logo_img,
                bg=self.colors["BG_SIDEBAR"],
            )
            lbl_logo.pack(pady=(0, 10))
            self.lbl_logo = lbl_logo
        except Exception as e:
            # Si el archivo existe pero no se pudo cargar (formato no
            # soportado, archivo corrupto, etc.), no se rompe la app.
            print(f"[Logo] No se pudo cargar '{ruta_logo}': {e}")

    # ------------------------------------------------------------------
    # TEMA: MODO OSCURO / MODO CLARO
    # ------------------------------------------------------------------
    def _texto_boton_tema(self):
        return "☀  Modo claro" if self.modo_oscuro else "🌙  Modo oscuro"

    def alternar_tema(self):
        """Cambia entre modo oscuro y modo claro, recoloreando en vivo
        todos los widgets ya construidos (sidebar, chat, burbujas,
        historial, panel de PDFs, etc.)."""
        colores_anteriores = dict(self.colors)
        self.modo_oscuro = not self.modo_oscuro
        self.colors = dict(PALETA_OSCURA if self.modo_oscuro else PALETA_CLARA)

        # Mapa "color viejo -> color nuevo" para recolorear por valor,
        # así no hace falta llevar un registro manual de cada widget.
        mapa = {
            colores_anteriores[clave]: self.colors[clave]
            for clave in colores_anteriores
        }

        self.configure(bg=self.colors["BG_MAIN"])
        self._recolorear_arbol(self, mapa)

        self.btn_tema.configure(text=self._texto_boton_tema())

    def _recolorear_arbol(self, widget, mapa):
        """Recorre recursivamente todos los widgets descendientes y
        actualiza sus colores según el mapa de traducción de paleta."""
        self._recolorear_widget(widget, mapa)
        for hijo in widget.winfo_children():
            self._recolorear_arbol(hijo, mapa)

    def _recolorear_widget(self, widget, mapa):
        propiedades = (
            "bg", "fg", "background", "foreground",
            "activebackground", "activeforeground",
            "highlightbackground", "highlightcolor",
            "insertbackground", "selectbackground", "selectforeground",
            "troughcolor", "disabledforeground",
        )
        for prop in propiedades:
            try:
                actual = widget.cget(prop)
            except tk.TclError:
                continue
            if actual in mapa:
                try:
                    widget.configure(**{prop: mapa[actual]})
                except tk.TclError:
                    pass

    def _crear_item_nav(self, parent, icono, texto, command=None):
        """Crea un botón de acceso rápido tipo 'icono + texto', al estilo
        de los ítems de navegación en interfaces de IA (Claude, Copilot, etc.)."""
        item = tk.Frame(parent, bg=self.colors["BG_SIDEBAR"], cursor="hand2")
        item.pack(fill="x", pady=1)

        lbl_icono = tk.Label(
            item,
            text=icono,
            font=self.font_normal,
            bg=self.colors["BG_SIDEBAR"],
            fg=self.colors["ACCENT"],
            width=2,
        )
        lbl_icono.pack(side="left", padx=(8, 4), pady=8)

        lbl_texto = tk.Label(
            item,
            text=texto,
            font=self.font_normal,
            bg=self.colors["BG_SIDEBAR"],
            fg=self.colors["TEXT_PRIMARY"],
            anchor="w",
        )
        lbl_texto.pack(side="left", fill="x", expand=True, pady=8)

        widgets = (item, lbl_icono, lbl_texto)

        def on_click(event=None):
            if command:
                command()

        def on_enter(event=None):
            for w in widgets:
                w.configure(bg=self.colors["BG_INPUT"])

        def on_leave(event=None):
            for w in widgets:
                w.configure(bg=self.colors["BG_SIDEBAR"])

        for w in widgets:
            w.bind("<Button-1>", on_click)
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)

        return item

    # ------------------------------------------------------------------
    # PANEL DESPLEGABLE DE JURISPRUDENCIAS / PDFS
    # ------------------------------------------------------------------
    def _construir_panel_pdf(self, parent):
        """Panel lateral (tipo tarjeta) que aparece junto al sidebar al dar
        clic en 'Jurisprudencia'. Permite seleccionar PDFs y abrirlos."""
        self.panel_pdf = tk.Frame(
            parent,
            bg=self.colors["BG_SIDEBAR"],
            width=280,
            highlightbackground=self.colors["BORDER"],
            highlightthickness=1,
        )
        self.panel_pdf.pack_propagate(False)
        # No se hace pack() aquí: se muestra/oculta en abrir_jurisprudencia()

        # --- Cabecera del panel ---
        header_pdf = tk.Frame(self.panel_pdf, bg=self.colors["BG_SIDEBAR"])
        header_pdf.pack(fill="x", padx=10, pady=10)

        lbl_titulo = tk.Label(
            header_pdf,
            text="📁 Jurisprudencias PDF",
            font=self.font_bold,
            bg=self.colors["BG_SIDEBAR"],
            fg=self.colors["ACCENT"],
            anchor="w",
        )
        lbl_titulo.pack(side="left", fill="x", expand=True)

        btn_cerrar = tk.Button(
            header_pdf,
            text="✕",
            font=self.font_bold,
            bg=self.colors["BG_SIDEBAR"],
            fg=self.colors["TEXT_SECONDARY"],
            bd=0,
            cursor="hand2",
            command=self.abrir_jurisprudencia,
        )
        btn_cerrar.pack(side="right")

        # --- Contenedor con la lista de PDFs seleccionados ---
        self.frame_lista_pdf = tk.Frame(self.panel_pdf, bg=self.colors["BG_SIDEBAR"])
        self.frame_lista_pdf.pack(fill="both", expand=True, padx=8, pady=5)

        # --- Botón para releer la carpeta fija de PDFs ---
        btn_recargar = tk.Button(
            self.panel_pdf,
            text="🔄  Actualizar carpeta",
            font=self.font_small,
            bg=self.colors["BG_INPUT"],
            fg=self.colors["TEXT_PRIMARY"],
            bd=1,
            relief="solid",
            cursor="hand2",
            command=self._refrescar_lista_pdfs,
        )
        btn_recargar.pack(fill="x", padx=10, pady=(0, 10))

    def abrir_jurisprudencia(self):
        """Muestra u oculta el panel lateral de jurisprudencias (PDFs)."""
        if self.panel_pdf_visible:
            self.panel_pdf.pack_forget()
            self.panel_pdf_visible = False
        else:
            # Se empaqueta justo a la derecha del sidebar principal
            self.panel_pdf.pack(side="left", fill="y", after=self.sidebar)
            self.panel_pdf_visible = True
            self._refrescar_lista_pdfs()

    def _refrescar_lista_pdfs(self):
        """Escanea la carpeta fija CARPETA_PDFS y redibuja la lista de PDFs
        encontrados dentro del panel."""
        for w in self.frame_lista_pdf.winfo_children():
            w.destroy()

        try:
            archivos = sorted(
                f for f in os.listdir(CARPETA_PDFS) if f.lower().endswith(".pdf")
            )
        except FileNotFoundError:
            try:
                os.makedirs(CARPETA_PDFS)
            except OSError:
                pass
            archivos = []

        if not archivos:
            lbl_vacio = tk.Label(
                self.frame_lista_pdf,
                text=f"No hay PDFs en:\n{CARPETA_PDFS}\n\nColoca ahí tus archivos\ny pulsa 'Actualizar carpeta'.",
                font=self.font_small,
                bg=self.colors["BG_SIDEBAR"],
                fg=self.colors["TEXT_SECONDARY"],
                justify="center",
                wraplength=240,
            )
            lbl_vacio.pack(pady=20)
            return

        for nombre in archivos:
            ruta = os.path.join(CARPETA_PDFS, nombre)
            nombre_corto = nombre if len(nombre) < 22 else nombre[:19] + "..."

            item = tk.Frame(
                self.frame_lista_pdf,
                bg=self.colors["BG_INPUT"],
                cursor="hand2",
                highlightbackground=self.colors["BORDER"],
                highlightthickness=1,
            )
            item.pack(fill="x", pady=4, padx=2)

            lbl_ic = tk.Label(item, text="📄", bg=self.colors["BG_INPUT"], font=self.font_normal)
            lbl_ic.pack(side="left", padx=(6, 2), pady=6)

            lbl_txt = tk.Label(
                item,
                text=nombre_corto,
                bg=self.colors["BG_INPUT"],
                font=self.font_small,
                fg=self.colors["TEXT_PRIMARY"],
                anchor="w",
            )
            lbl_txt.pack(side="left", fill="x", expand=True, pady=6)

            # Clic en el ícono o el nombre abre el PDF
            for w in (item, lbl_ic, lbl_txt):
                w.bind("<Button-1>", lambda e, r=ruta: self._abrir_pdf(r))

    def _abrir_pdf(self, ruta_archivo):
        """Abre el PDF con el lector predeterminado del sistema operativo."""
        try:
            sistema = platform.system()
            if sistema == "Windows":
                os.startfile(ruta_archivo)  # type: ignore[attr-defined]
            elif sistema == "Darwin":
                subprocess.Popen(["open", ruta_archivo])
            else:
                subprocess.Popen(["xdg-open", ruta_archivo])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el archivo:\n{e}")

    def abrir_sentencias(self):
        # TODO: conectar con el módulo/consulta de Sentencias
        print("Abrir sección: Sentencias")

    def _refrescar_historial(self):
        for w in self.frame_historial.winfo_children():
            w.destroy()

        for conv in reversed(list(self.conversaciones.values())):
            activo = conv.id == self.conversacion_actual
            bg = self.colors["BG_INPUT"] if activo else self.colors["BG_SIDEBAR"]
            item = tk.Label(
                self.frame_historial,
                text=conv.titulo,
                font=self.font_normal,
                bg=bg,
                fg=self.colors["TEXT_PRIMARY"],
                anchor="w",
                padx=10,
                pady=8,
                cursor="hand2",
            )
            item.pack(fill="x", pady=2)
            item.bind("<Button-1>", lambda e, cid=conv.id: self.cambiar_conversacion(cid))
            item.bind("<Enter>", lambda e, lbl=item, act=activo: lbl.configure(
                bg=self.colors["BG_INPUT"] if not act else bg))
            item.bind("<Leave>", lambda e, lbl=item, b=bg: lbl.configure(bg=b))

    # ------------------------------------------------------------------
    # PANEL DE CHAT
    # ------------------------------------------------------------------
    def _construir_panel_chat(self, parent):
        self.panel_chat = tk.Frame(parent, bg=self.colors["BG_MAIN"])
        self.panel_chat.pack(side="left", fill="both", expand=True)

        # --- Cabecera ---
        header = tk.Frame(self.panel_chat, bg=self.colors["BG_MAIN"], height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        self.lbl_titulo_conv = tk.Label(
            header,
            text="Nueva conversación",
            font=self.font_titulo,
            bg=self.colors["BG_MAIN"],
            fg=self.colors["TEXT_PRIMARY"],
        )
        self.lbl_titulo_conv.pack(side="left", padx=20, pady=10)

        # --- Área de mensajes (canvas + scrollbar) ---
        area_wrapper = tk.Frame(self.panel_chat, bg=self.colors["BG_MAIN"])
        area_wrapper.pack(fill="both", expand=True, padx=0, pady=0)

        self.canvas = tk.Canvas(area_wrapper, bg=self.colors["BG_MAIN"], highlightthickness=0)
        self.scrollbar = tk.Scrollbar(area_wrapper, orient="vertical", command=self.canvas.yview)
        self.frame_mensajes = tk.Frame(self.canvas, bg=self.colors["BG_MAIN"])

        self.frame_mensajes.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.frame_mensajes, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # --- Zona de entrada de texto ---
        self._construir_zona_entrada()

    def _on_canvas_resize(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _construir_zona_entrada(self):
        contenedor_input = tk.Frame(self.panel_chat, bg=self.colors["BG_MAIN"])
        contenedor_input.pack(fill="x", padx=24, pady=(0, 20))

        caja = tk.Frame(contenedor_input, bg=self.colors["BG_INPUT"], highlightbackground=self.colors["BORDER"],
                         highlightthickness=1, bd=0)
        caja.pack(fill="x")

        self.entry_texto = tk.Text(
            caja,
            height=3,
            bg=self.colors["BG_INPUT"],
            fg=self.colors["TEXT_PRIMARY"],
            insertbackground=self.colors["TEXT_PRIMARY"],
            font=self.font_normal,
            relief="flat",
            bd=0,
            wrap="word",
            padx=14,
            pady=12,
        )
        self.entry_texto.pack(side="left", fill="both", expand=True)
        self.entry_texto.bind("<Return>", self._on_enter_presionado)
        self.entry_texto.bind("<Shift-Return>", lambda e: None)  # permite salto de línea

        self.btn_enviar = tk.Button(
            caja,
            text="➤",
            font=self.font_bold,
            bg=self.colors["ACCENT"],
            fg="white",
            activebackground=self.colors["ACCENT_HOVER"],
            activeforeground="white",
            relief="flat",
            bd=0,
            width=3,
            cursor="hand2",
            command=self.enviar_mensaje,
        )
        self.btn_enviar.pack(side="right", padx=8, pady=8, anchor="s")

        lbl_hint = tk.Label(
            contenedor_input,
            text="Enter para enviar · Shift+Enter para nueva línea",
            font=self.font_small,
            bg=self.colors["BG_MAIN"],
            fg=self.colors["TEXT_SECONDARY"],
        )
        lbl_hint.pack(anchor="e", pady=(4, 0))

    def _on_enter_presionado(self, event):
        # Enter envía el mensaje; Shift+Enter agrega salto de línea (manejado arriba)
        self.enviar_mensaje()
        return "break"

    # ------------------------------------------------------------------
    # LÓGICA DE CONVERSACIONES
    # ------------------------------------------------------------------
    def nueva_conversacion(self):
        conv = Conversacion()
        self.conversaciones[conv.id] = conv
        self.conversacion_actual = conv.id
        self.lbl_titulo_conv.configure(text=conv.titulo)
        self._limpiar_area_mensajes()
        self._refrescar_historial()
        self._mostrar_bienvenida()

    def cambiar_conversacion(self, conv_id):
        if self.generando:
            return
        self.conversacion_actual = conv_id
        conv = self.conversaciones[conv_id]
        self.lbl_titulo_conv.configure(text=conv.titulo)
        self._limpiar_area_mensajes()
        if not conv.mensajes:
            self._mostrar_bienvenida()
        else:
            for m in conv.mensajes:
                self._agregar_burbuja(m.autor, m.texto)
        self._refrescar_historial()

    def _limpiar_area_mensajes(self):
        for w in self.frame_mensajes.winfo_children():
            w.destroy()

    def _mostrar_bienvenida(self):
        lbl = tk.Label(
            self.frame_mensajes,
            text="¿En qué puedo ayudarte hoy?",
            font=tkfont.Font(family=FONT_FAMILY, size=20, weight="bold"),
            bg=self.colors["BG_MAIN"],
            fg=self.colors["TEXT_PRIMARY"],
        )
        lbl.pack(pady=(80, 0))

    # ------------------------------------------------------------------
    # ENVÍO DE MENSAJES
    # ------------------------------------------------------------------
    def enviar_mensaje(self):
        if self.generando:
            return

        texto = self.entry_texto.get("1.0", "end").strip()
        if not texto:
            return

        self.entry_texto.delete("1.0", "end")

        conv = self.conversaciones[self.conversacion_actual]

        # Si es el primer mensaje, limpiar mensaje de bienvenida y usarlo como título
        if not conv.mensajes:
            self._limpiar_area_mensajes()
            conv.titulo = (texto[:28] + "…") if len(texto) > 28 else texto
            self.lbl_titulo_conv.configure(text=conv.titulo)
            self._refrescar_historial()

        conv.mensajes.append(Mensaje("user", texto))
        self._agregar_burbuja("user", texto)

        # Indicador de "escribiendo…"
        self.generando = True
        self.btn_enviar.configure(state="disabled")
        indicador = self._agregar_burbuja("ia", "Pensando…", devolver_widget=True)

        # Llamada a la IA en un hilo aparte para no congelar la interfaz
        hilo = threading.Thread(target=self._hilo_generar_respuesta, args=(texto, indicador))
        hilo.daemon = True
        hilo.start()

    def _hilo_generar_respuesta(self, texto_usuario, widget_indicador):
        respuesta = generar_respuesta_ia(texto_usuario)
        # Volver al hilo principal de Tkinter para actualizar la interfaz
        self.after(0, lambda: self._finalizar_respuesta(respuesta, widget_indicador))

    def _finalizar_respuesta(self, respuesta, widget_indicador):
        conv = self.conversaciones[self.conversacion_actual]
        conv.mensajes.append(Mensaje("ia", respuesta))

        # Reemplaza el texto del indicador "Pensando…" por la respuesta real
        widget_indicador.configure(text=respuesta)

        self.generando = False
        self.btn_enviar.configure(state="normal")
        self._scroll_al_final()

    # ------------------------------------------------------------------
    # RENDERIZADO DE BURBUJAS DE CHAT
    # ------------------------------------------------------------------
    def _agregar_burbuja(self, autor, texto, devolver_widget=False):
        es_usuario = autor == "user"

        fila = tk.Frame(self.frame_mensajes, bg=self.colors["BG_MAIN"])
        fila.pack(fill="x", padx=20, pady=8, anchor="e" if es_usuario else "w")

        bg_burbuja = self.colors["BG_BUBBLE_USER"] if es_usuario else self.colors["BG_BUBBLE_IA"]
        etiqueta_autor = "Tú" if es_usuario else "Asistente"

        contenedor = tk.Frame(fila, bg=self.colors["BG_MAIN"])
        contenedor.pack(anchor="e" if es_usuario else "w")

        lbl_autor = tk.Label(
            contenedor,
            text=etiqueta_autor,
            font=self.font_small,
            bg=self.colors["BG_MAIN"],
            fg=self.colors["TEXT_SECONDARY"],
            anchor="e" if es_usuario else "w",
        )
        lbl_autor.pack(fill="x")

        burbuja = tk.Frame(
            contenedor,
            bg=bg_burbuja,
            highlightbackground=self.colors["BORDER"],
            highlightthickness=1 if es_usuario else 0,
        )
        burbuja.pack(anchor="e" if es_usuario else "w", pady=(2, 0))

        ancho_max = 70  # caracteres aprox. antes de hacer wrap
        lbl_texto = tk.Label(
            burbuja,
            text=texto,
            font=self.font_normal,
            bg=bg_burbuja,
            fg=self.colors["TEXT_PRIMARY"],
            justify="left",
            anchor="w",
            wraplength=560,
            padx=14,
            pady=10,
        )
        lbl_texto.pack()

        self._scroll_al_final()
        return lbl_texto if devolver_widget else None

    def _scroll_al_final(self):
        self.update_idletasks()
        self.canvas.yview_moveto(1.0)


# ----------------------------------------------------------------------
# CONEXIÓN CON EL MODELO DE IA
# ----------------------------------------------------------------------
def generar_respuesta_ia(mensaje_usuario: str) -> str:
    """
    Punto de integración con tu backend de IA.

    Reemplaza el contenido de esta función para conectar con:
      - La API de Anthropic (Claude) usando el SDK 'anthropic'
      - La API de OpenAI
      - Un modelo local (Ollama, llama.cpp, etc.)

    Ejemplo con la API de Anthropic (requiere `pip install anthropic`
    y una variable de entorno ANTHROPIC_API_KEY):

        import anthropic
        client = anthropic.Anthropic()
        respuesta = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": mensaje_usuario}],
        )
        return respuesta.content[0].text

    Por ahora, esta función solo simula una respuesta con un pequeño retraso.
    """
    time.sleep(1.2)  # simula latencia de red
    return (
        "Esto es una respuesta de ejemplo. Conecta la función "
        "generar_respuesta_ia() a tu modelo de IA real (Claude, "
        "OpenAI, un modelo local, etc.) para reemplazar este texto.\n\n"
        f"Tu mensaje fue: \"{mensaje_usuario}\""
    )


if __name__ == "__main__":
    app = IAApp()
    app.mainloop()
