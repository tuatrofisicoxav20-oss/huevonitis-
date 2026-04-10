from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from config import (
    AUTOSAVE_DIR,
    BACKUPS_DIR,
    DEFAULT_MARGIN_BOTTOM,
    DEFAULT_MARGIN_LEFT,
    DEFAULT_MARGIN_RIGHT,
    DEFAULT_MARGIN_TOP,
    DEFAULT_PAGE_HEIGHT,
    DEFAULT_PAGE_WIDTH,
    PROJECTS_DIR,
)
from core.models import Page, Project
from core.serializer import load_project_json, save_project_json


class ProjectManager:
    def create_project(self, name: str, subject: str = "General") -> Project:
        project = Project(name=name, subject=subject)
        first_page = Page(
            width=DEFAULT_PAGE_WIDTH,
            height=DEFAULT_PAGE_HEIGHT,
            margin_top=DEFAULT_MARGIN_TOP,
            margin_left=DEFAULT_MARGIN_LEFT,
            margin_right=DEFAULT_MARGIN_RIGHT,
            margin_bottom=DEFAULT_MARGIN_BOTTOM,
        )
        project.add_page(first_page)
        return project

    def add_page(self, project: Project) -> Page:
        page = Page(
            width=DEFAULT_PAGE_WIDTH,
            height=DEFAULT_PAGE_HEIGHT,
            margin_top=DEFAULT_MARGIN_TOP,
            margin_left=DEFAULT_MARGIN_LEFT,
            margin_right=DEFAULT_MARGIN_RIGHT,
            margin_bottom=DEFAULT_MARGIN_BOTTOM,
        )
        project.add_page(page)
        return page

    def _safe_name(self, name: str) -> str:
        clean = name.strip().replace(" ", "_")
        return clean or "proyecto"

    def default_project_path(self, project: Project) -> Path:
        return PROJECTS_DIR / f"{self._safe_name(project.name)}_{project.id[:8]}.json"

    def autosave_path(self, project: Project) -> Path:
        return AUTOSAVE_DIR / f"{self._safe_name(project.name)}_{project.id[:8]}_autosave.json"

    def backup_path(self, project: Project) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return BACKUPS_DIR / f"{self._safe_name(project.name)}_{project.id[:8]}_{stamp}.json"

    def save_project(self, project: Project, file_path: Optional[Path] = None) -> Path:
        if file_path is None:
            file_path = self.default_project_path(project)

        if file_path.exists():
            save_project_json(self.backup_path(project), project)

        save_project_json(file_path, project)
        return file_path

    def autosave_project(self, project: Project) -> Path:
        path = self.autosave_path(project)
        save_project_json(path, project)
        return path

    def open_project(self, file_path: Path) -> Project:
        return load_project_json(file_path)