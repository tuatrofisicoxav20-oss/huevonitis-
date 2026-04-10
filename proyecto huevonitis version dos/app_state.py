from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AppState:
    current_project: Optional[object] = None
    current_page_id: Optional[str] = None
    selected_tool: str = "select"
    selected_element_id: Optional[str] = None
    has_unsaved_changes: bool = False
    zoom: float = 1.0
    current_file_path: Optional[str] = None
    undo_stack: List[dict] = field(default_factory=list)
    redo_stack: List[dict] = field(default_factory=list)

    def set_current_project(self, project: object) -> None:
        self.current_project = project
        if getattr(project, "pages", None):
            self.current_page_id = project.pages[0].id
        else:
            self.current_page_id = None
        self.has_unsaved_changes = False
        self.undo_stack.clear()
        self.redo_stack.clear()

    def set_current_page(self, page_id: str) -> None:
        self.current_page_id = page_id

    def mark_dirty(self) -> None:
        self.has_unsaved_changes = True

    def mark_saved(self) -> None:
        self.has_unsaved_changes = False