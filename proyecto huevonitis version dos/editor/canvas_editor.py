import tkinter as tk
from pathlib import Path
from typing import Optional

from PIL import Image, ImageTk

from core.models import ImageElement, LineElement, Page, RectElement, TableElement, TextElement
from editor.selection_tool import SelectionTool


class CanvasEditor(tk.Frame):
    def __init__(self, master, on_change=None, on_select=None):
        super().__init__(master, bg="#d9d9d9")

        self.canvas = tk.Canvas(self, bg="#cfcfcf", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.current_page: Optional[Page] = None
        self.selection_tool = SelectionTool()
        self.selected_element_id: Optional[str] = None
        self.on_change = on_change
        self.on_select = on_select

        self._image_cache = {}
        self._page_origin = (0, 0)

        self.canvas.bind("<Button-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)

    def load_page(self, page: Page) -> None:
        self.current_page = page
        self.selected_element_id = None
        self.render_page()

    def render_page(self) -> None:
        self.canvas.delete("all")
        self._image_cache.clear()

        if not self.current_page:
            return

        page = self.current_page
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width <= 1:
            canvas_width = 1200
        if canvas_height <= 1:
            canvas_height = 900

        x0 = (canvas_width - page.width) / 2
        y0 = 30
        x1 = x0 + page.width
        y1 = y0 + page.height
        self._page_origin = (x0, y0)

        self.canvas.create_rectangle(x0 + 6, y0 + 6, x1 + 6, y1 + 6, fill="#b9b9b9", outline="")
        self.canvas.create_rectangle(x0, y0, x1, y1, fill="white", outline="#999999", width=1)

        self.canvas.create_line(
            x0 + page.margin_left, y0, x0 + page.margin_left, y1, fill="#e08a8a"
        )

        self.canvas.create_text(
            x1 - 20,
            y0 + 20,
            text=str(page.page_number),
            anchor="ne",
            fill="#777777",
            font=("Arial", 12),
        )

        for element in page.elements:
            self._draw_element(element, x0, y0)

        self._draw_selection(x0, y0)

    def _draw_element(self, element, page_x: float, page_y: float) -> None:
        if not element.visible:
            return

        if isinstance(element, TextElement):
            self.canvas.create_text(
                page_x + element.x,
                page_y + element.y,
                text=element.text,
                anchor="nw",
                fill=element.color,
                font=("Arial", element.font_size),
                width=element.width,
            )

        elif isinstance(element, ImageElement):
            image_path = Path(element.image_path)
            if not image_path.exists():
                self.canvas.create_rectangle(
                    page_x + element.x,
                    page_y + element.y,
                    page_x + element.x + element.width,
                    page_y + element.y + element.height,
                    outline="red",
                )
                self.canvas.create_text(
                    page_x + element.x + 10,
                    page_y + element.y + 10,
                    anchor="nw",
                    text="Imagen no encontrada",
                    fill="red",
                )
                return

            pil_img = Image.open(image_path).convert("RGBA")
            pil_img = pil_img.resize((max(1, int(element.width)), max(1, int(element.height))))
            tk_img = ImageTk.PhotoImage(pil_img)
            self._image_cache[element.id] = tk_img

            self.canvas.create_image(
                page_x + element.x,
                page_y + element.y,
                image=tk_img,
                anchor="nw",
            )

        elif isinstance(element, RectElement):
            self.canvas.create_rectangle(
                page_x + element.x,
                page_y + element.y,
                page_x + element.x + element.width,
                page_y + element.y + element.height,
                fill=element.fill_color,
                outline=element.outline_color,
                width=element.outline_width,
            )

        elif isinstance(element, LineElement):
            self.canvas.create_line(
                page_x + element.x,
                page_y + element.y,
                page_x + element.x + element.width,
                page_y + element.y + element.height,
                fill=element.color,
                width=element.line_width,
            )

        elif isinstance(element, TableElement):
            element.ensure_shape()
            x = page_x + element.x
            y = page_y + element.y
            w = max(40, element.width)
            h = max(40, element.height)
            cell_w = w / element.cols
            cell_h = h / element.rows

            self.canvas.create_rectangle(
                x, y, x + w, y + h,
                outline=element.line_color,
                width=element.line_width
            )

            for c in range(1, element.cols):
                cx = x + c * cell_w
                self.canvas.create_line(cx, y, cx, y + h, fill=element.line_color, width=element.line_width)

            for r in range(1, element.rows):
                ry = y + r * cell_h
                self.canvas.create_line(x, ry, x + w, ry, fill=element.line_color, width=element.line_width)

            for r in range(element.rows):
                for c in range(element.cols):
                    txt = element.cell_text[r][c]
                    if txt.strip():
                        tx = x + c * cell_w + 6
                        ty = y + r * cell_h + 6
                        self.canvas.create_text(
                            tx,
                            ty,
                            text=txt,
                            anchor="nw",
                            fill=element.text_color,
                            font=("Arial", element.font_size),
                            width=max(20, cell_w - 12),
                        )

    def _draw_selection(self, page_x: float, page_y: float) -> None:
        if not self.current_page or not self.selected_element_id:
            return

        element = self.current_page.get_element(self.selected_element_id)
        if not element:
            return

        outline = "#2b7cff" if not getattr(element, "locked", False) else "#ff8c42"

        self.canvas.create_rectangle(
            page_x + element.x - 3,
            page_y + element.y - 3,
            page_x + element.x + element.width + 3,
            page_y + element.y + element.height + 3,
            outline=outline,
            width=2,
            dash=(4, 2),
        )

        if getattr(element, "locked", False):
            self.canvas.create_text(
                page_x + element.x,
                page_y + element.y - 10,
                anchor="sw",
                text="🔒 Bloqueado",
                fill="#ff8c42",
                font=("Arial", 10, "bold"),
            )

    def _canvas_to_page_coords(self, canvas_x: float, canvas_y: float):
        x0, y0 = self._page_origin
        return canvas_x - x0, canvas_y - y0

    def _on_mouse_down(self, event) -> None:
        if not self.current_page:
            return

        page_x, page_y = self._canvas_to_page_coords(event.x, event.y)
        element = self.selection_tool.find_element_at(self.current_page, page_x, page_y)

        if element:
            self.selected_element_id = element.id
            self.selection_tool.start_drag(element, page_x, page_y)
            if self.on_select:
                self.on_select(element.id)
        else:
            self.selected_element_id = None
            if self.on_select:
                self.on_select(None)

        self.render_page()

    def _on_mouse_drag(self, event) -> None:
        if not self.current_page or not self.selection_tool.dragging:
            return

        page_x, page_y = self._canvas_to_page_coords(event.x, event.y)
        moved = self.selection_tool.update_drag(self.current_page, page_x, page_y)
        if moved:
            self.render_page()
            if self.on_change:
                self.on_change()

    def _on_mouse_up(self, _event) -> None:
        self.selection_tool.end_drag()

    def set_selected_element(self, element_id: Optional[str]) -> None:
        self.selected_element_id = element_id
        self.render_page()

    def on_resize(self, _event=None) -> None:
        self.render_page()