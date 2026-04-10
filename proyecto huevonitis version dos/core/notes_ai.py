from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


@dataclass
class NoteBlock:
    kind: str  # title, subtitle, bullet, paragraph
    text: str


def normalize_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sentences(text: str) -> List[str]:
    text = normalize_text(text)
    if not text:
        return []
    parts = re.split(r'(?<=[.!?])\s+|\n+', text)
    return [p.strip() for p in parts if p.strip()]


def clean_phrase(text: str) -> str:
    text = text.strip("•-–— \n\t")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def pick_title(sentences: List[str]) -> str:
    if not sentences:
        return "APUNTES"

    first = clean_phrase(sentences[0])

    # Si parece encabezado corto, úsalo casi directo
    if len(first.split()) <= 8 and len(first) <= 60:
        return first.upper()

    # Si empieza con "La...", "El...", "Los..." etc, intenta resumir
    words = first.split()[:6]
    title = " ".join(words).strip(".,;:")
    if not title:
        title = "APUNTES"

    return title.upper()


def sentence_topic(sentence: str) -> str:
    s = sentence.lower()

    rules = [
        ("Definición", [" es ", " se define", " consiste en", " se refiere a"]),
        ("Características", ["característica", " se compone", " incluye", " presenta", " posee"]),
        ("Función", [" sirve", " permite", " ayuda", " funciona", " se utiliza"]),
        ("Proceso", [" proceso", " ocurre", " sucede", " etapa", " paso", " durante"]),
        ("Importancia", [" importante", " relevancia", " fundamental", " esencial", " destaca"]),
        ("Causas", [" causa", " debido", " porque", " provoca", " origin"]),
        ("Consecuencias", [" consecuencia", " resultado", " genera", " produce", " ocasiona"]),
        ("Ejemplos", [" ejemplo", " como ", " tales como", " por ejemplo"]),
        ("Clasificación", [" tipos", " clases", " se divide", " se clasific", " categoría"]),
        ("Ubicación", [" se encuentra", " está en", " ocurre en", " ubicado", " localiza"]),
    ]

    for label, patterns in rules:
        for p in patterns:
            if p in s:
                return label

    return "Ideas clave"


def shorten_bullet(sentence: str, max_words: int = 18) -> str:
    sentence = clean_phrase(sentence)
    words = sentence.split()
    if len(words) <= max_words:
        return sentence

    short = " ".join(words[:max_words]).rstrip(".,;:")
    return short + "..."


def cluster_sentences(sentences: List[str]) -> List[tuple[str, List[str]]]:
    sections: List[tuple[str, List[str]]] = []

    for sentence in sentences:
        topic = sentence_topic(sentence)

        if not sections:
            sections.append((topic, [sentence]))
            continue

        last_topic, items = sections[-1]

        if topic == last_topic and len(items) < 4:
            items.append(sentence)
        else:
            sections.append((topic, [sentence]))

    return sections


def build_note_blocks(text: str) -> List[NoteBlock]:
    sentences = split_sentences(text)
    if not sentences:
        return [NoteBlock("title", "APUNTES"), NoteBlock("paragraph", "No hay contenido suficiente.")]

    title = pick_title(sentences)
    sections = cluster_sentences(sentences)

    blocks: List[NoteBlock] = [NoteBlock("title", title)]

    for subtitle, items in sections[:8]:
        blocks.append(NoteBlock("subtitle", subtitle))
        for item in items[:4]:
            blocks.append(NoteBlock("bullet", shorten_bullet(item)))

    # Resumen final
    summary_items = [shorten_bullet(s, 14) for s in sentences[:3]]
    if summary_items:
        blocks.append(NoteBlock("subtitle", "Resumen"))
        for item in summary_items:
            blocks.append(NoteBlock("bullet", item))

    return blocks