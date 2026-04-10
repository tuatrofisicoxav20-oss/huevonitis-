from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from uuid import uuid4


def generate_id() -> str:
    return uuid4().hex


@dataclass
class BaseElement:
    id: str = field(default_factory=generate_id)
    type: str = "base"
    x: float = 0
    y: float = 0
    width: float = 100
    height: float = 40
    rotation: float = 0.0
    visible: bool = True
    locked: bool = False
    z_index: int = 0


@dataclass
class TextElement(BaseElement):
    type: str = "text"
    text: str = "Nuevo texto"
    font_size: int = 24
    color: str = "#111111"


@dataclass
class ImageElement(BaseElement):
    type: str = "image"
    image_path: str = ""


@dataclass
class RectElement(BaseElement):
    type: str = "rect"
    fill_color: str = "#fff4c2"
    outline_color: str = "#444444"
    outline_width: int = 2


@dataclass
class LineElement(BaseElement):
    type: str = "line"
    color: str = "#222222"
    line_width: int = 3


@dataclass
class TableElement(BaseElement):
    type: str = "table"
    rows: int = 3
    cols: int = 3
    cell_text: List[List[str]] = field(default_factory=list)
    line_color: str = "#333333"
    line_width: int = 2
    font_size: int = 14
    text_color: str = "#111111"

    def ensure_shape(self) -> None:
        if self.rows < 1:
            self.rows = 1
        if self.cols < 1:
            self.cols = 1

        while len(self.cell_text) < self.rows:
            self.cell_text.append(["" for _ in range(self.cols)])

        if len(self.cell_text) > self.rows:
            self.cell_text = self.cell_text[:self.rows]

        for r in range(self.rows):
            while len(self.cell_text[r]) < self.cols:
                self.cell_text[r].append("")
            if len(self.cell_text[r]) > self.cols:
                self.cell_text[r] = self.cell_text[r][:self.cols]


@dataclass
class ServiceOrder:
    client_name: str = ""
    delivery_type: str = "Apunte premium"
    style_preset: str = "Escolar limpio"
    handwriting_mode: str = "Manuscrita premium"
    teacher_name: str = ""
    school_name: str = ""
    due_date: str = ""
    notes: str = ""
    use_handwriting: bool = True
    include_cover: bool = False
    accent_color: str = "#1d4ed8"

    def summary(self) -> str:
        client = self.client_name.strip() or "Sin cliente"
        due = self.due_date.strip() or "Sin fecha"
        return f"{client} | {self.delivery_type} | {self.style_preset} | {due}"


@dataclass
class Page:
    id: str = field(default_factory=generate_id)
    width: int = 900
    height: int = 1200
    background_type: str = "blank"
    page_number: int = 1
    title: str = ""
    margin_top: int = 80
    margin_left: int = 70
    margin_right: int = 70
    margin_bottom: int = 80
    elements: List[BaseElement] = field(default_factory=list)

    def add_element(self, element: BaseElement) -> None:
        self.elements.append(element)
        self.sort_elements()

    def remove_element(self, element_id: str) -> None:
        self.elements = [e for e in self.elements if e.id != element_id]

    def get_element(self, element_id: str) -> Optional[BaseElement]:
        for element in self.elements:
            if element.id == element_id:
                return element
        return None

    def sort_elements(self) -> None:
        self.elements.sort(key=lambda e: e.z_index)

    def display_name(self) -> str:
        if self.title.strip():
            return f"{self.page_number}. {self.title.strip()}"
        return f"{self.page_number}. Página {self.page_number}"


@dataclass
class Project:
    id: str = field(default_factory=generate_id)
    name: str = "Proyecto sin nombre"
    subject: str = "General"
    pages: List[Page] = field(default_factory=list)
    service_order: ServiceOrder = field(default_factory=ServiceOrder)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)

    def add_page(self, page: Page) -> None:
        page.page_number = len(self.pages) + 1
        if not page.title.strip():
            page.title = f"Página {page.page_number}"
        self.pages.append(page)

    def remove_page(self, page_id: str) -> None:
        self.pages = [p for p in self.pages if p.id != page_id]
        for i, page in enumerate(self.pages, start=1):
            page.page_number = i
            if not page.title.strip() or page.title.startswith("Página "):
                page.title = f"Página {i}"

    def get_page(self, page_id: str) -> Optional[Page]:
        for page in self.pages:
            if page.id == page_id:
                return page
        return None