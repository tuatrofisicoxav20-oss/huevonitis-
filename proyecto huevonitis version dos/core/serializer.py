from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from core.models import (
    ImageElement,
    LineElement,
    Page,
    Project,
    RectElement,
    ServiceOrder,
    TableElement,
    TextElement,
)


def element_to_dict(element) -> Dict[str, Any]:
    return asdict(element)


def element_from_dict(data: Dict[str, Any]):
    element_type = data.get("type", "text")

    if element_type == "text":
        return TextElement(**data)
    if element_type == "image":
        return ImageElement(**data)
    if element_type == "rect":
        return RectElement(**data)
    if element_type == "line":
        return LineElement(**data)
    if element_type == "table":
        element = TableElement(**data)
        element.ensure_shape()
        return element

    return TextElement(**data)


def page_to_dict(page: Page) -> Dict[str, Any]:
    return {
        "id": page.id,
        "width": page.width,
        "height": page.height,
        "background_type": page.background_type,
        "page_number": page.page_number,
        "title": page.title,
        "margin_top": page.margin_top,
        "margin_left": page.margin_left,
        "margin_right": page.margin_right,
        "margin_bottom": page.margin_bottom,
        "elements": [element_to_dict(e) for e in page.elements],
    }


def page_from_dict(data: Dict[str, Any]) -> Page:
    page = Page(
        id=data["id"],
        width=data["width"],
        height=data["height"],
        background_type=data.get("background_type", "blank"),
        page_number=data.get("page_number", 1),
        title=data.get("title", ""),
        margin_top=data.get("margin_top", 80),
        margin_left=data.get("margin_left", 70),
        margin_right=data.get("margin_right", 70),
        margin_bottom=data.get("margin_bottom", 80),
    )
    page.elements = [element_from_dict(e) for e in data.get("elements", [])]
    page.sort_elements()
    return page


def service_order_to_dict(order: ServiceOrder) -> Dict[str, Any]:
    return asdict(order)


def service_order_from_dict(data: Dict[str, Any]) -> ServiceOrder:
    return ServiceOrder(**data)


def project_to_dict(project: Project) -> Dict[str, Any]:
    return {
        "id": project.id,
        "name": project.name,
        "subject": project.subject,
        "pages": [page_to_dict(p) for p in project.pages],
        "service_order": service_order_to_dict(project.service_order),
        "tags": list(project.tags),
        "metadata": dict(project.metadata),
    }


def project_from_dict(data: Dict[str, Any]) -> Project:
    project = Project(
        id=data["id"],
        name=data["name"],
        subject=data.get("subject", "General"),
        service_order=service_order_from_dict(data.get("service_order", {})),
        tags=data.get("tags", []),
        metadata=data.get("metadata", {}),
    )
    project.pages = [page_from_dict(p) for p in data.get("pages", [])]
    return project


def save_project_json(path: Path, project: Project) -> None:
    path.write_text(
        json.dumps(project_to_dict(project), indent=4, ensure_ascii=False),
        encoding="utf-8",
    )


def load_project_json(path: Path) -> Project:
    data = json.loads(path.read_text(encoding="utf-8"))
    return project_from_dict(data)