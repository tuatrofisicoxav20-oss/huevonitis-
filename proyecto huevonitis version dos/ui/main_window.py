import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, simpledialog

from PIL import Image

from app_state import AppState
from config import (
    APP_TITLE,
    AUTOSAVE_INTERVAL_MS,
    DATA_DIR,
    HANDWRITING_DIR,
    PREVIEWS_DIR,
)
from core import features
from core.features import export_page_to_pdf
from core.models import (
    ImageElement,
    LineElement,
    RectElement,
    TableElement,
    TextElement,
)
from core.notes_ai import build_note_blocks
from core.project_manager import ProjectManager
from core.serializer import project_from_dict, project_to_dict, save_project_json
from editor.canvas_editor import CanvasEditor


class MainWindow(tk.Tk):
    STYLE_OPTIONS = ["Escolar limpio", "Premium oscuro", "Escolar cálido"]
    DELIVERY_OPTIONS = [
        "Apunte premium",
        "Tarea premium",
        "Guía de estudio",
        "Resumen visual",
        "Tabla comparativa",
    ]
    HANDWRITING_OPTIONS = [
        "Manuscrita premium",
        "Manuscrita rápida",
        "Manuscrita limpia",
    ]

    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry("1600x980")
        self.minsize(1280, 800)
        self.configure(bg="#dfe3ea")

        self.state_manager = AppState()
        self.project_manager = ProjectManager()

        self.cards = []
        self.exam_index = 0

        self.colors = {
            "app_bg": "#dfe3ea",
            "panel_bg": "#eef1f5",
            "section_bg": "#f8fafc",
            "toolbar_bg": "#1f2937",
            "toolbar_fg": "#ffffff",
            "accent": "#2563eb",
            "accent_soft": "#dbeafe",
            "danger": "#b91c1c",
            "text": "#111827",
            "muted": "#6b7280",
            "border": "#cbd5e1",
            "canvas_wrap": "#cfd6df",
        }

        self._build_ui()
        self._bind_events()

        self.create_new_project()
        self.after(AUTOSAVE_INTERVAL_MS, self._autosave_job)

    def _build_ui(self) -> None:
        self._build_topbar()

        body = tk.PanedWindow(
            self,
            sashrelief="flat",
            sashwidth=7,
            bg=self.colors["app_bg"],
            bd=0,
        )
        body.pack(fill="both", expand=True, padx=8, pady=(6, 0))

        left_panel = tk.Frame(body, bg=self.colors["panel_bg"], width=430)
        body.add(left_panel, minsize=380)

        right_shell = tk.Frame(body, bg=self.colors["canvas_wrap"])
        body.add(right_shell)

        self._build_left_panel(left_panel)
        self._build_right_panel(right_shell)
        self._build_statusbar()

    def _build_topbar(self) -> None:
        topbar = tk.Frame(self, bg=self.colors["toolbar_bg"], height=62)
        topbar.pack(side="top", fill="x")
        topbar.pack_propagate(False)

        title_wrap = tk.Frame(topbar, bg=self.colors["toolbar_bg"])
        title_wrap.pack(side="left", padx=12, pady=8)

        tk.Label(
            title_wrap,
            text="Huevonitis 2.0",
            font=("Segoe UI", 15, "bold"),
            fg=self.colors["toolbar_fg"],
            bg=self.colors["toolbar_bg"],
        ).pack(anchor="w")

        tk.Label(
            title_wrap,
            text="Modo servicio + manuscrito premium",
            font=("Segoe UI", 9),
            fg="#cbd5e1",
            bg=self.colors["toolbar_bg"],
        ).pack(anchor="w")

        tools_wrap = tk.Frame(topbar, bg=self.colors["toolbar_bg"])
        tools_wrap.pack(side="left", fill="x", expand=True, padx=10, pady=8)

        self._build_toolbar_group(
            tools_wrap,
            "Archivo",
            [
                ("Nuevo", self.create_new_project),
                ("Guardar", self.save_project),
                ("Abrir", self.open_project),
                ("PDF", self.export_pdf),
                ("Pack", self.export_service_pack_ui),
            ],
        ).pack(side="left", padx=6)

        self._build_toolbar_group(
            tools_wrap,
            "Servicio",
            [
                ("Pedido", self.edit_service_order),
                ("Preset", self.choose_style_preset),
                ("Preview", self.preview_current_page),
                ("Portada", self.generate_cover_page),
            ],
        ).pack(side="left", padx=6)

        self._build_toolbar_group(
            tools_wrap,
            "Insertar",
            [
                ("Página", self.add_page),
                ("Texto", self.add_text),
                ("Imagen", self.add_image),
                ("Rect", self.add_rectangle),
                ("Línea", self.add_line),
                ("Tabla", self.add_table),
                ("Mi letra", self.insert_typography_text),
            ],
        ).pack(side="left", padx=6)

        self._build_toolbar_group(
            tools_wrap,
            "Estudio",
            [
                ("OCR", self.import_ocr_image),
                ("Word", self.import_word),
                ("Resumen", self.show_summary),
                ("Preguntas", self.show_questions),
                ("Flashcards", self.show_flashcards),
                ("Conceptos", self.show_concepts),
                ("Examen", self.start_exam),
                ("Apunte Pro", self.generate_pro_notes),
                ("Apunte Manuscrito", self.generate_pro_notes_handwritten),
            ],
        ).pack(side="left", padx=6)

        self._build_toolbar_group(
            tools_wrap,
            "Editar",
            [
                ("Deshacer", self.undo),
                ("Rehacer", self.redo),
            ],
        ).pack(side="left", padx=6)

        info_wrap = tk.Frame(topbar, bg=self.colors["toolbar_bg"])
        info_wrap.pack(side="right", padx=12, pady=8)

        self.info_label = tk.Label(
            info_wrap,
            text="Sin proyecto",
            fg="white",
            bg=self.colors["toolbar_bg"],
            font=("Segoe UI", 10, "bold"),
            justify="right",
        )
        self.info_label.pack(anchor="e")

    def _build_toolbar_group(self, parent, title: str, actions: list[tuple[str, object]]) -> tk.Frame:
        box = tk.Frame(parent, bg="#334155", bd=0, highlightthickness=0)

        tk.Label(
            box,
            text=title,
            fg="#cbd5e1",
            bg="#334155",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=8, pady=(5, 0))

        btn_row = tk.Frame(box, bg="#334155")
        btn_row.pack(padx=6, pady=(3, 6))

        for text, cmd in actions:
            tk.Button(
                btn_row,
                text=text,
                command=cmd,
                bg="#e5e7eb",
                fg="#111827",
                activebackground="#ffffff",
                relief="flat",
                bd=0,
                padx=8,
                pady=4,
                font=("Segoe UI", 9),
                cursor="hand2",
            ).pack(side="left", padx=2)

        return box

    def _build_left_panel(self, parent) -> None:
        header = tk.Frame(parent, bg=self.colors["panel_bg"])
        header.pack(fill="x", padx=10, pady=(10, 8))

        tk.Label(
            header,
            text="Panel de control",
            font=("Segoe UI", 14, "bold"),
            fg=self.colors["text"],
            bg=self.colors["panel_bg"],
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Servicio, páginas, texto base y propiedades",
            font=("Segoe UI", 9),
            fg=self.colors["muted"],
            bg=self.colors["panel_bg"],
        ).pack(anchor="w", pady=(2, 0))

        self._build_service_panel(parent)
        self._build_pages_panel(parent)

        text_box_frame = self._section_frame(parent, "Entrada / texto base", "Aquí pegas texto, OCR o Word")
        text_box_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.text_input = tk.Text(
            text_box_frame,
            wrap="word",
            font=("Consolas", 12),
            height=9,
            bg="white",
            fg=self.colors["text"],
            relief="flat",
            bd=0,
            insertbackground=self.colors["text"],
        )
        self.text_input.pack(fill="x", padx=10, pady=(0, 10))

        self._build_properties_panel(parent)

    def _build_service_panel(self, parent) -> None:
        box = self._section_frame(parent, "Pedido de servicio", "Lo que sí vende, aquí empieza")
        box.pack(fill="x", padx=10, pady=(0, 10))

        self.service_summary_var = tk.StringVar(value="Sin pedido configurado")
        tk.Label(
            box,
            textvariable=self.service_summary_var,
            font=("Segoe UI", 10, "bold"),
            fg=self.colors["text"],
            bg=self.colors["section_bg"],
            justify="left",
            wraplength=360,
        ).pack(anchor="w", padx=10, pady=(0, 8))

        row = tk.Frame(box, bg=self.colors["section_bg"])
        row.pack(fill="x", padx=10, pady=(0, 10))
        self._primary_button(row, "Editar pedido", self.edit_service_order).pack(side="left", fill="x", expand=True)
        self._soft_button(row, "Preset visual", self.choose_style_preset).pack(side="left", fill="x", expand=True, padx=(6, 0))

    def _build_right_panel(self, parent) -> None:
        canvas_shell = tk.Frame(parent, bg=self.colors["canvas_wrap"])
        canvas_shell.pack(fill="both", expand=True, padx=10, pady=10)

        top = tk.Frame(canvas_shell, bg=self.colors["canvas_wrap"])
        top.pack(fill="x", pady=(0, 8))

        tk.Label(
            top,
            text="Lienzo",
            font=("Segoe UI", 13, "bold"),
            fg=self.colors["text"],
            bg=self.colors["canvas_wrap"],
        ).pack(side="left")

        self.quick_status = tk.Label(
            top,
            text="Selecciona un elemento para editarlo",
            font=("Segoe UI", 9),
            fg=self.colors["muted"],
            bg=self.colors["canvas_wrap"],
        )
        self.quick_status.pack(side="right")

        editor_wrap = tk.Frame(
            canvas_shell,
            bg=self.colors["canvas_wrap"],
            bd=0,
            highlightthickness=1,
            highlightbackground="#b8c2cf",
        )
        editor_wrap.pack(fill="both", expand=True)

        self.editor = CanvasEditor(
            editor_wrap,
            on_change=self._on_editor_change,
            on_select=self._on_element_select,
        )
        self.editor.pack(fill="both", expand=True)

    def _build_statusbar(self) -> None:
        status = tk.Frame(self, bg="#e5e7eb", height=30)
        status.pack(side="bottom", fill="x")
        status.pack_propagate(False)

        self.status_label = tk.Label(
            status,
            text="Listo",
            anchor="w",
            bg="#e5e7eb",
            fg=self.colors["text"],
            font=("Segoe UI", 9),
        )
        self.status_label.pack(side="left", fill="x", expand=True, padx=10)

    def _section_frame(self, parent, title: str, subtitle: str | None = None) -> tk.Frame:
        outer = tk.Frame(
            parent,
            bg=self.colors["section_bg"],
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            bd=0,
        )

        tk.Label(
            outer,
            text=title,
            font=("Segoe UI", 11, "bold"),
            fg=self.colors["text"],
            bg=self.colors["section_bg"],
        ).pack(anchor="w", padx=10, pady=(8, 0))

        if subtitle:
            tk.Label(
                outer,
                text=subtitle,
                font=("Segoe UI", 8),
                fg=self.colors["muted"],
                bg=self.colors["section_bg"],
            ).pack(anchor="w", padx=10, pady=(1, 8))

        return outer

    def _build_pages_panel(self, parent) -> None:
        box = self._section_frame(parent, "Páginas", "Navega, renombra y elimina páginas")
        box.pack(fill="x", padx=10, pady=(0, 10))

        self.page_listbox = tk.Listbox(
            box,
            height=7,
            exportselection=False,
            relief="flat",
            bd=0,
            bg="white",
            fg=self.colors["text"],
            selectbackground=self.colors["accent"],
            selectforeground="white",
            font=("Segoe UI", 10),
        )
        self.page_listbox.pack(fill="x", padx=10, pady=(0, 10))
        self.page_listbox.bind("<<ListboxSelect>>", self._on_page_list_select)

        nav = tk.Frame(box, bg=self.colors["section_bg"])
        nav.pack(fill="x", padx=10, pady=(0, 8))

        self._soft_button(nav, "◀ Anterior", self.go_prev_page).pack(side="left", fill="x", expand=True)
        self._soft_button(nav, "Siguiente ▶", self.go_next_page).pack(side="left", fill="x", expand=True, padx=(6, 0))

        actions = tk.Frame(box, bg=self.colors["section_bg"])
        actions.pack(fill="x", padx=10, pady=(0, 10))

        self._soft_button(actions, "Renombrar", self.rename_current_page).pack(side="left", fill="x", expand=True)
        self._danger_button(actions, "Eliminar", self.delete_current_page).pack(side="left", fill="x", expand=True, padx=(6, 0))

    def _build_properties_panel(self, parent) -> None:
        box = self._section_frame(parent, "Propiedades del elemento", "Edita el objeto seleccionado")
        box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.prop_title = tk.Label(
            box,
            text="Ningún elemento seleccionado",
            bg=self.colors["section_bg"],
            fg=self.colors["text"],
            anchor="w",
            font=("Segoe UI", 10, "bold"),
        )
        self.prop_title.pack(fill="x", padx=10, pady=(0, 8))

        row1 = tk.Frame(box, bg=self.colors["section_bg"])
        row1.pack(fill="x", padx=10, pady=2)
        tk.Label(row1, text="Tipo:", width=10, anchor="w", bg=self.colors["section_bg"]).pack(side="left")
        self.prop_type_var = tk.StringVar(value="-")
        tk.Label(row1, textvariable=self.prop_type_var, anchor="w", bg=self.colors["section_bg"]).pack(side="left")

        row2 = tk.Frame(box, bg=self.colors["section_bg"])
        row2.pack(fill="x", padx=10, pady=2)
        tk.Label(row2, text="X:", width=10, anchor="w", bg=self.colors["section_bg"]).pack(side="left")
        self.prop_x_var = tk.StringVar(value="")
        self._entry(row2, self.prop_x_var, 10).pack(side="left", padx=(0, 10))
        tk.Label(row2, text="Y:", width=4, anchor="w", bg=self.colors["section_bg"]).pack(side="left")
        self.prop_y_var = tk.StringVar(value="")
        self._entry(row2, self.prop_y_var, 10).pack(side="left")

        row3 = tk.Frame(box, bg=self.colors["section_bg"])
        row3.pack(fill="x", padx=10, pady=2)
        tk.Label(row3, text="Ancho:", width=10, anchor="w", bg=self.colors["section_bg"]).pack(side="left")
        self.prop_width_var = tk.StringVar(value="")
        self._entry(row3, self.prop_width_var, 10).pack(side="left", padx=(0, 10))
        tk.Label(row3, text="Alto:", width=4, anchor="w", bg=self.colors["section_bg"]).pack(side="left")
        self.prop_height_var = tk.StringVar(value="")
        self._entry(row3, self.prop_height_var, 10).pack(side="left")

        row4 = tk.Frame(box, bg=self.colors["section_bg"])
        row4.pack(fill="x", padx=10, pady=2)
        tk.Label(row4, text="Fuente:", width=10, anchor="w", bg=self.colors["section_bg"]).pack(side="left")
        self.prop_font_var = tk.StringVar(value="")
        self.prop_font_entry = self._entry(row4, self.prop_font_var, 10)
        self.prop_font_entry.pack(side="left", padx=(0, 10))
        tk.Label(row4, text="Color:", width=4, anchor="w", bg=self.colors["section_bg"]).pack(side="left")
        self.prop_color_var = tk.StringVar(value="#111111")
        self.prop_color_entry = self._entry(row4, self.prop_color_var, 12)
        self.prop_color_entry.pack(side="left", padx=(0, 4))
        self._soft_button(row4, "🎨", self.pick_color, width=3).pack(side="left")

        row5 = tk.Frame(box, bg=self.colors["section_bg"])
        row5.pack(fill="x", padx=10, pady=2)
        tk.Label(row5, text="Extra 1:", width=10, anchor="w", bg=self.colors["section_bg"]).pack(side="left")
        self.prop_extra1_var = tk.StringVar(value="")
        self._entry(row5, self.prop_extra1_var, 12).pack(side="left", padx=(0, 10))
        tk.Label(row5, text="Extra 2:", width=8, anchor="w", bg=self.colors["section_bg"]).pack(side="left")
        self.prop_extra2_var = tk.StringVar(value="")
        self._entry(row5, self.prop_extra2_var, 12).pack(side="left")

        tk.Label(
            box,
            text="Texto / contenido:",
            anchor="w",
            bg=self.colors["section_bg"],
            fg=self.colors["text"],
        ).pack(fill="x", padx=10, pady=(8, 2))

        self.prop_text = tk.Text(
            box,
            height=8,
            wrap="word",
            relief="flat",
            bd=0,
            bg="white",
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
        )
        self.prop_text.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self.prop_locked_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            box,
            text="Bloquear elemento",
            variable=self.prop_locked_var,
            bg=self.colors["section_bg"],
            anchor="w",
        ).pack(fill="x", padx=10, pady=(0, 8))

        btns1 = tk.Frame(box, bg=self.colors["section_bg"])
        btns1.pack(fill="x", padx=10, pady=2)
        self._primary_button(btns1, "Aplicar cambios", self.apply_properties).pack(side="left", fill="x", expand=True)
        self._soft_button(btns1, "Refrescar", self.refresh_properties_panel).pack(side="left", fill="x", expand=True, padx=(6, 0))

        btns2 = tk.Frame(box, bg=self.colors["section_bg"])
        btns2.pack(fill="x", padx=10, pady=(6, 10))
        self._danger_button(btns2, "Eliminar seleccionado", self.delete_selected_element).pack(
            side="left", fill="x", expand=True
        )

    def _entry(self, parent, variable: tk.StringVar, width: int) -> tk.Entry:
        return tk.Entry(
            parent,
            textvariable=variable,
            width=width,
            relief="flat",
            bd=0,
            bg="white",
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
        )

    def _soft_button(self, parent, text, command, width=None) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            width=width,
            relief="flat",
            bd=0,
            bg="#e5e7eb",
            fg=self.colors["text"],
            activebackground="#d1d5db",
            activeforeground=self.colors["text"],
            font=("Segoe UI", 9),
            cursor="hand2",
            padx=8,
            pady=5,
        )

    def _primary_button(self, parent, text, command) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            relief="flat",
            bd=0,
            bg=self.colors["accent"],
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            padx=10,
            pady=6,
        )

    def _danger_button(self, parent, text, command) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            relief="flat",
            bd=0,
            bg=self.colors["danger"],
            fg="white",
            activebackground="#991b1b",
            activeforeground="white",
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            padx=10,
            pady=6,
        )

    def _bind_events(self) -> None:
        self.editor.canvas.bind("<Configure>", self.editor.on_resize)

    def _on_editor_change(self) -> None:
        self.state_manager.mark_dirty()
        self._refresh_labels()
        self.refresh_properties_panel()
        self.refresh_pages_list()

    def _on_element_select(self, element_id) -> None:
        self.state_manager.selected_element_id = element_id
        self.refresh_properties_panel()
        self._refresh_labels()

        if element_id:
            self.quick_status.config(text="Elemento seleccionado")
        else:
            self.quick_status.config(text="Sin selección")

    def _on_page_list_select(self, _event=None) -> None:
        selection = self.page_listbox.curselection()
        project = self._current_project()

        if not project or not selection:
            return

        index = selection[0]
        if 0 <= index < len(project.pages):
            page = project.pages[index]
            self.state_manager.current_page_id = page.id
            self.state_manager.selected_element_id = None
            self._load_current_page()
            self.refresh_properties_panel()
            self._refresh_labels()
            self.quick_status.config(text=f"Página activa: {page.display_name()}")

    def _current_project(self):
        return self.state_manager.current_project

    def _current_page(self):
        project = self._current_project()
        if not project or not self.state_manager.current_page_id:
            return None
        return project.get_page(self.state_manager.current_page_id)

    def _current_element(self):
        page = self._current_page()
        if not page or not self.state_manager.selected_element_id:
            return None
        return page.get_element(self.state_manager.selected_element_id)

    def _current_page_index(self) -> int:
        project = self._current_project()
        page = self._current_page()

        if not project or not page:
            return -1

        for i, p in enumerate(project.pages):
            if p.id == page.id:
                return i
        return -1

    def _snapshot(self) -> None:
        project = self._current_project()
        if not project:
            return
        self.state_manager.undo_stack.append(project_to_dict(project))
        if len(self.state_manager.undo_stack) > 50:
            self.state_manager.undo_stack.pop(0)
        self.state_manager.redo_stack.clear()

    def _restore_snapshot(self, snapshot: dict) -> None:
        project = project_from_dict(snapshot)
        self.state_manager.current_project = project
        if project.pages:
            if not (self.state_manager.current_page_id and project.get_page(self.state_manager.current_page_id)):
                self.state_manager.current_page_id = project.pages[0].id
        self._load_current_page()
        self.refresh_pages_list()
        self.refresh_properties_panel()
        self._refresh_labels()
        self._refresh_service_summary()

    def create_new_project(self) -> None:
        name = simpledialog.askstring("Nuevo proyecto", "Nombre del proyecto:", initialvalue="Mi cuaderno")
        if not name:
            name = "Mi cuaderno"

        subject = simpledialog.askstring("Materia", "Materia:", initialvalue="General")
        if not subject:
            subject = "General"

        project = self.project_manager.create_project(name=name, subject=subject)
        self.state_manager.set_current_project(project)
        self.state_manager.current_file_path = None
        self.state_manager.selected_element_id = None
        self.text_input.delete("1.0", tk.END)
        self._load_current_page()
        self.refresh_pages_list()
        self.refresh_properties_panel()
        self._refresh_labels()
        self._refresh_service_summary()
        self.status_label.config(text="Proyecto nuevo creado")
        self.quick_status.config(text="Proyecto recién creado")

    def _load_current_page(self) -> None:
        page = self._current_page()
        if page:
            self.editor.load_page(page)

    def _refresh_labels(self) -> None:
        project = self._current_project()
        if not project:
            self.info_label.config(text="Sin proyecto")
            return

        current_page = self._current_page()
        page_text = current_page.display_name() if current_page else "Sin página"
        dirty = " *" if self.state_manager.has_unsaved_changes else ""
        sel = self._current_element()
        sel_text = f" | Selección: {sel.type}" if sel else ""
        order_text = project.service_order.delivery_type if getattr(project, "service_order", None) else "Sin servicio"
        self.info_label.config(text=f"{project.name} | {project.subject} | {order_text}\n{page_text}{sel_text}{dirty}")

    def _refresh_service_summary(self) -> None:
        project = self._current_project()
        if not project:
            self.service_summary_var.set("Sin pedido configurado")
            return

        order = project.service_order
        client = order.client_name.strip() or "Sin cliente"
        due = order.due_date.strip() or "Sin fecha"
        note = f"{client}\n{order.delivery_type} | {order.style_preset}\nEntrega: {due}"
        self.service_summary_var.set(note)

    def save_project(self) -> None:
        project = self._current_project()
        if not project:
            return

        initial = self.state_manager.current_file_path or str(self.project_manager.default_project_path(project))
        file_path = filedialog.asksaveasfilename(
            title="Guardar proyecto",
            initialfile=Path(initial).name,
            defaultextension=".json",
            filetypes=[("Proyecto Huevonitis", "*.json")],
        )
        if not file_path:
            return

        try:
            path = self.project_manager.save_project(project, Path(file_path))
            self.state_manager.current_file_path = str(path)
            self.state_manager.mark_saved()
            self._refresh_labels()
            self.status_label.config(text=f"Proyecto guardado: {path.name}")
            self.quick_status.config(text="Guardado correcto")
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo guardar el proyecto.\n\n{exc}")

    def open_project(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Abrir proyecto",
            filetypes=[("Proyecto Huevonitis", "*.json")],
        )
        if not file_path:
            return

        try:
            project = self.project_manager.open_project(Path(file_path))
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo abrir el proyecto.\n\n{exc}")
            return

        self.state_manager.set_current_project(project)
        self.state_manager.current_file_path = file_path
        self.state_manager.selected_element_id = None
        self._load_current_page()
        self.refresh_pages_list()
        self.refresh_properties_panel()
        self._refresh_labels()
        self._refresh_service_summary()
        self.status_label.config(text="Proyecto abierto")
        self.quick_status.config(text="Proyecto cargado")

    def refresh_pages_list(self) -> None:
        project = self._current_project()
        self.page_listbox.delete(0, tk.END)

        if not project:
            return

        current_index = self._current_page_index()

        for page in project.pages:
            marker = "● " if page.id == self.state_manager.current_page_id else "○ "
            self.page_listbox.insert(tk.END, marker + page.display_name())

        if current_index != -1:
            self.page_listbox.selection_clear(0, tk.END)
            self.page_listbox.selection_set(current_index)
            self.page_listbox.activate(current_index)

    def go_prev_page(self) -> None:
        project = self._current_project()
        index = self._current_page_index()

        if not project or index <= 0:
            return

        self.state_manager.current_page_id = project.pages[index - 1].id
        self.state_manager.selected_element_id = None
        self._load_current_page()
        self.refresh_pages_list()
        self.refresh_properties_panel()
        self._refresh_labels()
        self.status_label.config(text="Página anterior")

    def go_next_page(self) -> None:
        project = self._current_project()
        index = self._current_page_index()

        if not project or index == -1 or index >= len(project.pages) - 1:
            return

        self.state_manager.current_page_id = project.pages[index + 1].id
        self.state_manager.selected_element_id = None
        self._load_current_page()
        self.refresh_pages_list()
        self.refresh_properties_panel()
        self._refresh_labels()
        self.status_label.config(text="Página siguiente")

    def rename_current_page(self) -> None:
        page = self._current_page()
        if not page:
            return

        nuevo = simpledialog.askstring(
            "Renombrar página",
            "Nuevo nombre para la página:",
            initialvalue=page.title or f"Página {page.page_number}"
        )
        if nuevo is None:
            return

        nuevo = nuevo.strip() or f"Página {page.page_number}"

        self._snapshot()
        page.title = nuevo
        self.state_manager.mark_dirty()
        self.refresh_pages_list()
        self._refresh_labels()
        self.status_label.config(text="Página renombrada")

    def delete_current_page(self) -> None:
        project = self._current_project()
        page = self._current_page()

        if not project or not page:
            return

        if len(project.pages) <= 1:
            messagebox.showwarning("Aviso", "Debe existir al menos una página en el proyecto.")
            return

        if not messagebox.askyesno("Confirmar", f"¿Eliminar {page.display_name()}?"):
            return

        self._snapshot()
        current_index = self._current_page_index()
        project.remove_page(page.id)

        new_index = max(0, min(current_index - 1, len(project.pages) - 1))
        self.state_manager.current_page_id = project.pages[new_index].id
        self.state_manager.selected_element_id = None
        self.state_manager.mark_dirty()

        self._load_current_page()
        self.refresh_pages_list()
        self.refresh_properties_panel()
        self._refresh_labels()
        self.status_label.config(text="Página eliminada")

    def edit_service_order(self) -> None:
        project = self._current_project()
        if not project:
            return

        order = project.service_order

        client_name = simpledialog.askstring("Pedido", "Nombre del cliente:", initialvalue=order.client_name or "")
        if client_name is None:
            return

        delivery_type = simpledialog.askstring(
            "Pedido",
            "Tipo de entrega:\nApunte premium / Tarea premium / Guía de estudio / Resumen visual / Tabla comparativa",
            initialvalue=order.delivery_type,
        )
        if delivery_type is None:
            return

        style_preset = simpledialog.askstring(
            "Pedido",
            f"Preset visual ({', '.join(self.STYLE_OPTIONS)}):",
            initialvalue=order.style_preset,
        )
        if style_preset is None:
            return

        handwriting_mode = simpledialog.askstring(
            "Pedido",
            f"Modo manuscrito ({', '.join(self.HANDWRITING_OPTIONS)}):",
            initialvalue=order.handwriting_mode,
        )
        if handwriting_mode is None:
            return

        teacher_name = simpledialog.askstring("Pedido", "Nombre del profe:", initialvalue=order.teacher_name or "")
        if teacher_name is None:
            teacher_name = order.teacher_name

        school_name = simpledialog.askstring("Pedido", "Escuela:", initialvalue=order.school_name or "")
        if school_name is None:
            school_name = order.school_name

        due_date = simpledialog.askstring("Pedido", "Fecha de entrega:", initialvalue=order.due_date or "")
        if due_date is None:
            due_date = order.due_date

        notes = simpledialog.askstring("Pedido", "Notas extra:", initialvalue=order.notes or "")
        if notes is None:
            notes = order.notes

        self._snapshot()
        order.client_name = client_name.strip()
        order.delivery_type = delivery_type.strip() or order.delivery_type
        order.style_preset = style_preset.strip() or order.style_preset
        order.handwriting_mode = handwriting_mode.strip() or order.handwriting_mode
        order.teacher_name = teacher_name.strip()
        order.school_name = school_name.strip()
        order.due_date = due_date.strip()
        order.notes = notes.strip()
        self.state_manager.mark_dirty()
        self._refresh_service_summary()
        self._refresh_labels()
        self.status_label.config(text="Pedido de servicio actualizado")

    def choose_style_preset(self) -> None:
        project = self._current_project()
        if not project:
            return

        preset = simpledialog.askstring(
            "Preset visual",
            f"Elige un preset:\n{', '.join(self.STYLE_OPTIONS)}",
            initialvalue=project.service_order.style_preset,
        )
        if preset is None:
            return

        preset = preset.strip()
        if not preset:
            return

        self._snapshot()
        project.service_order.style_preset = preset
        self.state_manager.mark_dirty()
        self._refresh_service_summary()
        self._refresh_labels()
        self.status_label.config(text=f"Preset aplicado: {preset}")

    def refresh_properties_panel(self) -> None:
        element = self._current_element()

        self.prop_text.config(state="normal")
        self.prop_font_entry.config(state="normal")
        self.prop_color_entry.config(state="normal")

        if not element:
            self.prop_title.config(text="Ningún elemento seleccionado")
            self.prop_type_var.set("-")
            self.prop_x_var.set("")
            self.prop_y_var.set("")
            self.prop_width_var.set("")
            self.prop_height_var.set("")
            self.prop_font_var.set("")
            self.prop_color_var.set("")
            self.prop_extra1_var.set("")
            self.prop_extra2_var.set("")
            self.prop_locked_var.set(False)
            self.prop_text.delete("1.0", tk.END)
            return

        self.prop_title.config(text=f"Elemento seleccionado: {element.id[:8]}")
        self.prop_type_var.set(element.type)
        self.prop_x_var.set(str(int(element.x)))
        self.prop_y_var.set(str(int(element.y)))
        self.prop_width_var.set(str(int(element.width)))
        self.prop_height_var.set(str(int(element.height)))
        self.prop_locked_var.set(bool(getattr(element, "locked", False)))
        self.prop_text.delete("1.0", tk.END)

        if isinstance(element, TextElement):
            self.prop_font_var.set(str(element.font_size))
            self.prop_color_var.set(element.color)
            self.prop_extra1_var.set("")
            self.prop_extra2_var.set("")
            self.prop_text.insert("1.0", element.text)

        elif isinstance(element, ImageElement):
            self.prop_font_var.set("")
            self.prop_color_var.set("")
            self.prop_extra1_var.set("")
            self.prop_extra2_var.set("")
            self.prop_text.insert("1.0", element.image_path)
            self.prop_text.config(state="disabled")
            self.prop_font_entry.config(state="disabled")
            self.prop_color_entry.config(state="disabled")

        elif isinstance(element, RectElement):
            self.prop_font_var.set(str(element.outline_width))
            self.prop_color_var.set(element.fill_color)
            self.prop_extra1_var.set(element.outline_color)
            self.prop_extra2_var.set("")
            self.prop_text.insert("1.0", "Rectángulo")

        elif isinstance(element, LineElement):
            self.prop_font_var.set(str(element.line_width))
            self.prop_color_var.set(element.color)
            self.prop_extra1_var.set("")
            self.prop_extra2_var.set("")
            self.prop_text.insert("1.0", "Línea")

        elif isinstance(element, TableElement):
            element.ensure_shape()
            self.prop_font_var.set(str(element.font_size))
            self.prop_color_var.set(element.text_color)
            self.prop_extra1_var.set(str(element.rows))
            self.prop_extra2_var.set(str(element.cols))
            flat_text = []
            for row in element.cell_text:
                flat_text.append(" | ".join(row))
            self.prop_text.insert("1.0", "\n".join(flat_text))

        self.editor.set_selected_element(element.id)

    def pick_color(self) -> None:
        element = self._current_element()
        if not element:
            return

        initial = self.prop_color_var.get().strip() or "#111111"
        chosen = colorchooser.askcolor(color=initial)[1]
        if chosen:
            self.prop_color_var.set(chosen)

    def _parse_table_text(self, text: str, rows: int, cols: int):
        lines = [line.strip() for line in text.splitlines()]
        data = []

        for line in lines[:rows]:
            parts = [p.strip() for p in line.split("|")]
            while len(parts) < cols:
                parts.append("")
            data.append(parts[:cols])

        while len(data) < rows:
            data.append(["" for _ in range(cols)])

        return data

    def apply_properties(self) -> None:
        element = self._current_element()
        if not element:
            messagebox.showwarning("Aviso", "No hay elemento seleccionado")
            return

        try:
            self._snapshot()

            element.x = max(0, float(self.prop_x_var.get()))
            element.y = max(0, float(self.prop_y_var.get()))
            element.width = max(20, float(self.prop_width_var.get()))
            element.height = max(20, float(self.prop_height_var.get()))
            element.locked = bool(self.prop_locked_var.get())

            if isinstance(element, TextElement):
                element.font_size = max(8, int(self.prop_font_var.get()))
                element.color = self.prop_color_var.get().strip() or "#111111"
                element.text = self.prop_text.get("1.0", tk.END).strip() or "Nuevo texto"
                line_count = max(1, element.text.count("\n") + 1)
                element.height = max(element.height, line_count * (element.font_size + 10))

            elif isinstance(element, RectElement):
                element.outline_width = max(1, int(self.prop_font_var.get() or 2))
                element.fill_color = self.prop_color_var.get().strip() or "#fff4c2"
                element.outline_color = self.prop_extra1_var.get().strip() or "#444444"

            elif isinstance(element, LineElement):
                element.line_width = max(1, int(self.prop_font_var.get() or 3))
                element.color = self.prop_color_var.get().strip() or "#222222"

            elif isinstance(element, TableElement):
                element.rows = max(1, int(self.prop_extra1_var.get() or 1))
                element.cols = max(1, int(self.prop_extra2_var.get() or 1))
                element.font_size = max(8, int(self.prop_font_var.get() or 14))
                element.text_color = self.prop_color_var.get().strip() or "#111111"
                element.cell_text = self._parse_table_text(
                    self.prop_text.get("1.0", tk.END).strip(),
                    element.rows,
                    element.cols,
                )
                element.ensure_shape()

            self.state_manager.mark_dirty()
            self._load_current_page()
            self.refresh_properties_panel()
            self.refresh_pages_list()
            self.status_label.config(text="Propiedades aplicadas")
        except ValueError:
            messagebox.showerror("Error", "Revisa los campos numéricos. Hay un valor inválido.")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def delete_selected_element(self) -> None:
        page = self._current_page()
        element = self._current_element()

        if not page or not element:
            messagebox.showwarning("Aviso", "No hay elemento seleccionado")
            return

        if not messagebox.askyesno("Confirmar", "¿Eliminar el elemento seleccionado?"):
            return

        self._snapshot()
        page.remove_element(element.id)
        self.state_manager.selected_element_id = None
        self.state_manager.mark_dirty()
        self._load_current_page()
        self.refresh_properties_panel()
        self.refresh_pages_list()
        self.status_label.config(text="Elemento eliminado")

    def add_page(self) -> None:
        project = self._current_project()
        if not project:
            return

        self._snapshot()
        page = self.project_manager.add_page(project)
        self.state_manager.current_page_id = page.id
        self.state_manager.selected_element_id = None
        self.state_manager.mark_dirty()
        self._load_current_page()
        self.refresh_pages_list()
        self.refresh_properties_panel()
        self._refresh_labels()
        self.status_label.config(text="Página agregada")

    def add_text(self) -> None:
        page = self._current_page()
        if not page:
            return

        text = simpledialog.askstring("Agregar texto", "Escribe el texto:", initialvalue="Apunte nuevo")
        if not text:
            return

        self._snapshot()
        element = TextElement(
            x=100, y=120 + len(page.elements) * 60, width=600, height=80, text=text, font_size=24
        )
        page.add_element(element)
        self.state_manager.selected_element_id = element.id
        self.state_manager.mark_dirty()
        self._load_current_page()
        self.refresh_pages_list()
        self.refresh_properties_panel()
        self.status_label.config(text="Texto agregado")

    def add_image(self) -> None:
        page = self._current_page()
        if not page:
            return

        ruta = filedialog.askopenfilename(
            title="Insertar imagen",
            filetypes=[("Imagen", "*.png *.jpg *.jpeg *.bmp *.webp")]
        )
        if not ruta:
            return

        try:
            img = Image.open(ruta)
            w, h = img.size

            max_w = 500
            if w > max_w:
                scale = max_w / w
                w = int(w * scale)
                h = int(h * scale)

            self._snapshot()
            element = ImageElement(
                x=100, y=120 + len(page.elements) * 40, width=w, height=h, image_path=ruta
            )
            page.add_element(element)
            self.state_manager.selected_element_id = element.id
            self.state_manager.mark_dirty()
            self._load_current_page()
            self.refresh_properties_panel()
            self.status_label.config(text="Imagen insertada")
        except Exception as exc:
            messagebox.showerror("Error imagen", str(exc))

    def add_rectangle(self) -> None:
        page = self._current_page()
        if not page:
            return

        self._snapshot()
        element = RectElement(
            x=100, y=120 + len(page.elements) * 30, width=220, height=120
        )
        page.add_element(element)
        self.state_manager.selected_element_id = element.id
        self.state_manager.mark_dirty()
        self._load_current_page()
        self.refresh_properties_panel()
        self.status_label.config(text="Rectángulo agregado")

    def add_line(self) -> None:
        page = self._current_page()
        if not page:
            return

        self._snapshot()
        element = LineElement(
            x=100, y=120 + len(page.elements) * 30, width=220, height=0
        )
        page.add_element(element)
        self.state_manager.selected_element_id = element.id
        self.state_manager.mark_dirty()
        self._load_current_page()
        self.refresh_properties_panel()
        self.status_label.config(text="Línea agregada")

    def add_table(self) -> None:
        page = self._current_page()
        if not page:
            return

        rows = simpledialog.askinteger("Tabla", "Número de filas:", initialvalue=3, minvalue=1, maxvalue=20)
        if rows is None:
            return
        cols = simpledialog.askinteger("Tabla", "Número de columnas:", initialvalue=3, minvalue=1, maxvalue=20)
        if cols is None:
            return

        self._snapshot()
        element = TableElement(
            x=100,
            y=120 + len(page.elements) * 30,
            width=max(180, cols * 120),
            height=max(90, rows * 50),
            rows=rows,
            cols=cols,
            cell_text=[["" for _ in range(cols)] for _ in range(rows)],
        )
        element.ensure_shape()
        page.add_element(element)
        self.state_manager.selected_element_id = element.id
        self.state_manager.mark_dirty()
        self._load_current_page()
        self.refresh_properties_panel()
        self.status_label.config(text="Tabla agregada")

    def import_word(self) -> None:
        ruta = filedialog.askopenfilename(title="Abrir Word", filetypes=[("Word", "*.docx")])
        if not ruta:
            return

        try:
            texto = features.leer_word(ruta)
            self.text_input.delete("1.0", tk.END)
            self.text_input.insert(tk.END, texto)
            self.status_label.config(text="Texto de Word cargado")
        except Exception as exc:
            messagebox.showerror("Error Word", str(exc))

    def import_ocr_image(self) -> None:
        ruta = filedialog.askopenfilename(
            title="Abrir imagen para OCR",
            filetypes=[("Imagen", "*.png *.jpg *.jpeg *.bmp")]
        )
        if not ruta:
            return

        try:
            texto = features.leer_texto_imagen(ruta)
            self.text_input.delete("1.0", tk.END)
            self.text_input.insert(tk.END, texto)
            self.status_label.config(text="OCR completado")
        except Exception as exc:
            messagebox.showerror("Error OCR", str(exc))

    def insert_typography_text(self) -> None:
        page = self._current_page()
        if not page:
            return

        texto = self.text_input.get("1.0", tk.END).strip()
        if not texto:
            texto = simpledialog.askstring("Mi letra", "Escribe el texto a convertir:")
            if not texto:
                return

        try:
            self._snapshot()

            out_path = HANDWRITING_DIR / f"hand_{len(page.elements)+1}.png"
            saved_path = features.save_typography_image(
                texto=texto,
                folder_tipografia="tipografia",
                out_path=out_path,
                max_width=1200,
                title_mode=False,
            )

            img = Image.open(saved_path)
            w, h = img.size

            max_w = 650
            if w > max_w:
                scale = max_w / w
                w = int(w * scale)
                h = int(h * scale)

            element = ImageElement(
                x=100,
                y=120 + len(page.elements) * 70,
                width=w,
                height=h,
                image_path=str(saved_path),
            )
            page.add_element(element)
            self.state_manager.selected_element_id = element.id
            self.state_manager.mark_dirty()
            self._load_current_page()
            self.refresh_pages_list()
            self.refresh_properties_panel()
            self.status_label.config(text="Texto manuscrito insertado")
        except Exception as exc:
            messagebox.showerror("Error tipografía", str(exc))

    def _add_handwriting_block(self, page, text: str, x: int, y: int, max_w: int, title_mode: bool = False):
        out_name = f"hand_{page.page_number}_{len(page.elements)+1}.png"
        out_path = HANDWRITING_DIR / out_name
        saved_path = features.save_typography_image(
            texto=text,
            folder_tipografia="tipografia",
            out_path=out_path,
            max_width=max_w,
            title_mode=title_mode,
        )
        img = Image.open(saved_path)
        element = ImageElement(
            x=x,
            y=y,
            width=img.width,
            height=img.height,
            image_path=str(saved_path),
        )
        page.add_element(element)
        return element

    def generate_pro_notes(self) -> None:
        page = self._current_page()
        if not page:
            return

        raw_text = self.text_input.get("1.0", tk.END).strip()
        if not raw_text:
            messagebox.showwarning("Aviso", "No hay texto base para convertir.")
            return

        blocks = build_note_blocks(raw_text)
        if not blocks:
            messagebox.showwarning("Aviso", "No se pudo generar el apunte.")
            return

        preset_name = self._current_project().service_order.style_preset
        preset = features.STYLE_PRESETS.get(preset_name, features.STYLE_PRESETS["Escolar limpio"])

        self._snapshot()

        y = 90
        x = 95
        max_width = 680
        created_ids = []

        for block in blocks:
            if block.kind == "title":
                element = TextElement(
                    x=x,
                    y=y,
                    width=max_width,
                    height=60,
                    text=block.text,
                    font_size=preset["title_font_size"],
                    color=preset["title_color"],
                )
                y += 70

            elif block.kind == "subtitle":
                element = TextElement(
                    x=x,
                    y=y,
                    width=max_width,
                    height=40,
                    text=block.text,
                    font_size=20,
                    color=preset["subtitle_color"],
                )
                y += 45

            elif block.kind == "bullet":
                element = TextElement(
                    x=x + 18,
                    y=y,
                    width=max_width - 20,
                    height=34,
                    text=f"• {block.text}",
                    font_size=preset["body_font_size"],
                    color=preset["body_color"],
                )
                y += 32

            else:
                element = TextElement(
                    x=x,
                    y=y,
                    width=max_width,
                    height=50,
                    text=block.text,
                    font_size=preset["body_font_size"],
                    color=preset["body_color"],
                )
                y += 42

            page.add_element(element)
            created_ids.append(element.id)

            if y > page.height - 120:
                break

        if created_ids:
            self.state_manager.selected_element_id = created_ids[-1]

        self.state_manager.mark_dirty()
        self._load_current_page()
        self.refresh_pages_list()
        self.refresh_properties_panel()
        self._refresh_labels()
        self.status_label.config(text="Apunte Pro generado")
        self.quick_status.config(text="Texto convertido en apunte estructurado")

    def generate_pro_notes_handwritten(self) -> None:
        page = self._current_page()
        if not page:
            return

        raw_text = self.text_input.get("1.0", tk.END).strip()
        if not raw_text:
            messagebox.showwarning("Aviso", "No hay texto base para convertir.")
            return

        blocks = build_note_blocks(raw_text)
        if not blocks:
            messagebox.showwarning("Aviso", "No se pudo generar el apunte.")
            return

        self._snapshot()

        y = 85
        x = 92
        max_width = 720
        last_id = None

        for block in blocks:
            if block.kind == "title":
                el = self._add_handwriting_block(page, block.text, x, y, max_width, title_mode=True)
                y += el.height + 18
            elif block.kind == "subtitle":
                rect = RectElement(
                    x=x - 8,
                    y=y - 4,
                    width=max_width - 80,
                    height=36,
                    fill_color="#eff6ff",
                    outline_color="#93c5fd",
                    outline_width=2,
                )
                page.add_element(rect)
                y += 4
                txt = TextElement(
                    x=x + 8,
                    y=y,
                    width=max_width - 120,
                    height=28,
                    text=block.text,
                    font_size=18,
                    color="#1d4ed8",
                )
                page.add_element(txt)
                y += 42
                last_id = txt.id
            else:
                prefix = "• " if block.kind == "bullet" else ""
                el = self._add_handwriting_block(page, prefix + block.text, x + 8, y, max_width - 20, title_mode=False)
                y += el.height + 10
                last_id = el.id

            if y > page.height - 160:
                break

        self.state_manager.selected_element_id = last_id
        self.state_manager.mark_dirty()
        self._load_current_page()
        self.refresh_pages_list()
        self.refresh_properties_panel()
        self._refresh_labels()
        self.status_label.config(text="Apunte manuscrito premium generado")

    def generate_cover_page(self) -> None:
        project = self._current_project()
        if not project:
            return

        self._snapshot()
        page = self.project_manager.add_page(project)
        page.title = "Portada"
        self.state_manager.current_page_id = page.id

        order = project.service_order
        preset = features.STYLE_PRESETS.get(order.style_preset, features.STYLE_PRESETS["Escolar limpio"])

        page.add_element(
            RectElement(
                x=90,
                y=120,
                width=720,
                height=280,
                fill_color=preset["rect_fill"],
                outline_color=preset["rect_outline"],
                outline_width=3,
            )
        )
        page.add_element(
            TextElement(
                x=120,
                y=160,
                width=650,
                height=60,
                text=project.name,
                font_size=30,
                color=preset["title_color"],
            )
        )
        page.add_element(
            TextElement(
                x=120,
                y=230,
                width=650,
                height=40,
                text=f"Materia: {project.subject}",
                font_size=18,
                color="#111827",
            )
        )
        page.add_element(
            TextElement(
                x=120,
                y=270,
                width=650,
                height=40,
                text=f"Cliente: {order.client_name or 'Sin cliente'}",
                font_size=18,
                color="#111827",
            )
        )
        page.add_element(
            TextElement(
                x=120,
                y=310,
                width=650,
                height=40,
                text=f"Entrega: {order.due_date or 'Sin fecha'}",
                font_size=18,
                color="#111827",
            )
        )

        self.state_manager.mark_dirty()
        self._load_current_page()
        self.refresh_pages_list()
        self.refresh_properties_panel()
        self._refresh_labels()
        self.status_label.config(text="Portada generada")

    def preview_current_page(self) -> None:
        page = self._current_page()
        if not page:
            return

        out_path = PREVIEWS_DIR / f"preview_{page.id[:8]}.png"
        try:
            features.render_page_preview(page, out_path)
            messagebox.showinfo("Preview", f"Preview generado en:\n{out_path}")
            self.status_label.config(text="Preview generado")
        except Exception as exc:
            messagebox.showerror("Error preview", str(exc))

    def export_service_pack_ui(self) -> None:
        project = self._current_project()
        page = self._current_page()
        if not project or not page:
            return

        try:
            export_dir = self.project_manager.export_folder(project)
            export_dir.mkdir(parents=True, exist_ok=True)

            json_path = export_dir / f"{project.name.replace(' ', '_')}.json"
            preview_path = export_dir / "preview.png"
            pdf_path = export_dir / "pagina_actual.pdf"
            info_path = export_dir / "pedido.json"

            save_project_json(json_path, project)
            features.render_page_preview(page, preview_path)
            export_page_to_pdf(page, str(pdf_path))
            features.export_service_pack(project, json_path, preview_path, pdf_path, info_path)

            messagebox.showinfo(
                "Pack exportado",
                f"Pack generado en:\n{export_dir}\n\nIncluye JSON, PDF, preview y pedido."
            )
            self.status_label.config(text="Pack de servicio exportado")
        except Exception as exc:
            messagebox.showerror("Error export pack", str(exc))

    def show_summary(self) -> None:
        texto = self.text_input.get("1.0", tk.END).strip()
        if not texto:
            messagebox.showwarning("Aviso", "No hay texto base")
            return

        res = features.generar_resumen(texto)
        messagebox.showinfo("Resumen", res or "No se pudo generar resumen.")

    def show_questions(self) -> None:
        texto = self.text_input.get("1.0", tk.END).strip()
        if not texto:
            messagebox.showwarning("Aviso", "No hay texto base")
            return

        preguntas = features.generar_preguntas(texto)
        messagebox.showinfo("Preguntas", "\n\n".join(preguntas) if preguntas else "No se generaron preguntas.")

    def show_flashcards(self) -> None:
        texto = self.text_input.get("1.0", tk.END).strip()
        if not texto:
            messagebox.showwarning("Aviso", "No hay texto base")
            return

        cards = features.generar_flashcards(texto)
        if not cards:
            messagebox.showwarning("Aviso", "No se pudieron generar flashcards")
            return

        resultado = ""
        for pregunta, respuesta in cards:
            resultado += f"P: {pregunta}\nR: {respuesta}\n\n"

        messagebox.showinfo("Flashcards", resultado)

    def show_concepts(self) -> None:
        texto = self.text_input.get("1.0", tk.END).strip()
        if not texto:
            messagebox.showwarning("Aviso", "No hay texto base")
            return

        conceptos = features.extraer_conceptos(texto)
        messagebox.showinfo("Conceptos", "\n".join(conceptos) if conceptos else "No se extrajeron conceptos.")

    def start_exam(self) -> None:
        texto = self.text_input.get("1.0", tk.END).strip()
        if not texto:
            messagebox.showwarning("Aviso", "No hay texto base")
            return

        self.cards = features.generar_examen(texto)
        self.exam_index = 0

        if not self.cards:
            messagebox.showwarning("Aviso", "No se pudo generar el examen")
            return

        self._exam_window()

    def _exam_window(self):
        self.exam_win = tk.Toplevel(self)
        self.exam_win.title("Modo Examen")
        self.exam_win.geometry("720x500")
        self.exam_win.configure(bg="#eef2ff")

        self.exam_lbl = tk.Label(
            self.exam_win,
            text="",
            wraplength=640,
            font=("Segoe UI", 15, "bold"),
            bg="#eef2ff",
            fg=self.colors["text"],
        )
        self.exam_lbl.pack(pady=15)

        self.exam_input = tk.Text(
            self.exam_win,
            width=70,
            height=8,
            relief="flat",
            bd=0,
            bg="white",
            fg=self.colors["text"],
        )
        self.exam_input.pack(pady=10)

        self.exam_result = tk.Label(
            self.exam_win,
            text="",
            wraplength=640,
            justify="left",
            bg="#eef2ff",
            fg=self.colors["text"],
        )
        self.exam_result.pack(pady=10)

        btns = tk.Frame(self.exam_win, bg="#eef2ff")
        btns.pack(pady=6)

        self._primary_button(btns, "Calificar", self._grade_exam).pack(side="left", padx=4)
        self._soft_button(btns, "Siguiente", self._next_exam).pack(side="left", padx=4)

        self._show_exam_q()

    def _show_exam_q(self):
        if self.exam_index >= len(self.cards):
            self.exam_lbl.config(text="🎉 Terminaste el examen")
            self.exam_input.delete("1.0", tk.END)
            return

        pregunta, _ = self.cards[self.exam_index]
        self.exam_lbl.config(text=pregunta)
        self.exam_input.delete("1.0", tk.END)
        self.exam_result.config(text="")

    def _grade_exam(self):
        usuario = self.exam_input.get("1.0", tk.END).strip()
        _, correcta = self.cards[self.exam_index]
        score = features.calificar(usuario, correcta)
        self.exam_result.config(text=f"Calificación: {score}/10\n\nRespuesta correcta:\n{correcta}")

    def _next_exam(self):
        self.exam_index += 1
        self._show_exam_q()

    def export_pdf(self) -> None:
        page = self._current_page()
        if not page:
            return

        ruta = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            title="Exportar página a PDF",
        )
        if not ruta:
            return

        try:
            export_page_to_pdf(page, ruta)
            messagebox.showinfo("Éxito", f"PDF guardado en:\n{ruta}")
        except Exception as exc:
            messagebox.showerror("Error PDF", str(exc))

    def _autosave_job(self) -> None:
        project = self._current_project()
        if project and self.state_manager.has_unsaved_changes:
            try:
                self.project_manager.autosave_project(project)
                self.status_label.config(text="Autosave realizado")
            except Exception:
                pass

        self.after(AUTOSAVE_INTERVAL_MS, self._autosave_job)

    def undo(self) -> None:
        if not self.state_manager.undo_stack:
            return

        current = project_to_dict(self._current_project())
        self.state_manager.redo_stack.append(current)
        snapshot = self.state_manager.undo_stack.pop()
        self._restore_snapshot(snapshot)
        self.state_manager.mark_dirty()
        self.status_label.config(text="Deshacer")

    def redo(self) -> None:
        if not self.state_manager.redo_stack:
            return

        current = project_to_dict(self._current_project())
        self.state_manager.undo_stack.append(current)
        snapshot = self.state_manager.redo_stack.pop()
        self._restore_snapshot(snapshot)
        self.state_manager.mark_dirty()
        self.status_label.config(text="Rehacer")