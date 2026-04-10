from __future__ import annotations

from typing import Optional, Tuple


class SelectionTool:
    def __init__(self):
        self.dragging = False
        self.drag_element_id: Optional[str] = None
        self.drag_start_mouse: Optional[Tuple[float, float]] = None
        self.drag_start_element_pos: Optional[Tuple[float, float]] = None

    def reset(self) -> None:
        self.dragging = False
        self.drag_element_id = None
        self.drag_start_mouse = None
        self.drag_start_element_pos = None

    def find_element_at(self, page, canvas_x: float, canvas_y: float):
        if not page:
            return None

        for element in reversed(page.elements):
            x1 = element.x
            y1 = element.y
            x2 = element.x + element.width
            y2 = element.y + element.height

            extra = 6 if getattr(element, "type", "") == "line" else 0

            if (x1 - extra) <= canvas_x <= (x2 + extra) and (y1 - extra) <= canvas_y <= (y2 + extra):
                return element

        return None

    def start_drag(self, element, mouse_x: float, mouse_y: float) -> None:
        if getattr(element, "locked", False):
            return

        self.dragging = True
        self.drag_element_id = element.id
        self.drag_start_mouse = (mouse_x, mouse_y)
        self.drag_start_element_pos = (element.x, element.y)

    def update_drag(self, page, mouse_x: float, mouse_y: float):
        if not self.dragging or not self.drag_element_id:
            return None

        element = page.get_element(self.drag_element_id)
        if not element or not self.drag_start_mouse or not self.drag_start_element_pos:
            return None

        if getattr(element, "locked", False):
            return None

        start_mouse_x, start_mouse_y = self.drag_start_mouse
        start_element_x, start_element_y = self.drag_start_element_pos

        dx = mouse_x - start_mouse_x
        dy = mouse_y - start_mouse_y

        element.x = start_element_x + dx
        element.y = start_element_y + dy
        return element

    def end_drag(self) -> None:
        self.reset()