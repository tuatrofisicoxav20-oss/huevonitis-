from __future__ import annotations

import os
import random
import re
from pathlib import Path
from typing import List, Tuple

from PIL import Image

try:
    import cv2
    import numpy as np
    import pytesseract
except Exception:
    cv2 = None
    np = None
    pytesseract = None

from docx import Document
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from core.models import ImageElement, Page, TextElement


def leer_word(ruta: str) -> str:
    doc = Document(ruta)
    return "\n".join(p.text for p in doc.paragraphs).strip()


def leer_texto_imagen(ruta: str) -> str:
    if cv2 is None or np is None or pytesseract is None:
        raise RuntimeError("OCR no disponible. Instala opencv-python, numpy y pytesseract.")

    img = cv2.imread(ruta)
    if img is None:
        raise FileNotFoundError(f"No se pudo abrir la imagen: {ruta}")

    img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge((l, a, b))
    img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, th1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    th2 = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 11, 3
    )

    combinado = cv2.bitwise_or(th1, th2)
    kernel = np.ones((2, 2), np.uint8)
    limpio = cv2.morphologyEx(combinado, cv2.MORPH_CLOSE, kernel)

    config = r"--oem 3 --psm 6 -l spa"
    texto = pytesseract.image_to_string(limpio, config=config)
    return texto.strip()


def cargar_tipografia(folder: str = "tipografia") -> dict:
    letras = {}

    if not os.path.exists(folder):
        return letras

    for archivo in os.listdir(folder):
        if not archivo.lower().endswith(".png"):
            continue

        clave = archivo.split("_")[0][0].lower()
        ruta = os.path.join(folder, archivo)

        try:
            img = Image.open(ruta).convert("RGBA")
        except Exception:
            continue

        letras.setdefault(clave, []).append(img)

    return letras


def escribir_con_letra(texto: str, letras: dict) -> Image.Image:
    texto = texto.lower()

    espacio = 20
    ancho_total = 0
    altura_max = 0

    for c in texto:
        if c in letras:
            img = random.choice(letras[c])
            ancho_total += img.width + 5
            altura_max = max(altura_max, img.height)
        elif c == " ":
            ancho_total += 30
        else:
            ancho_total += espacio

    ancho_total = max(ancho_total, 200)
    altura_max = max(altura_max, 120)

    lienzo = Image.new("RGBA", (ancho_total, altura_max + 20), (255, 255, 255, 0))

    x = 10
    base_y = 10

    for c in texto:
        if c in letras:
            img = random.choice(letras[c])
            angulo = random.randint(-2, 2)
            offset_y = random.randint(-3, 3)
            img_mod = img.rotate(angulo, expand=True)
            lienzo.paste(img_mod, (x, base_y + offset_y), img_mod)
            x += img_mod.width + random.randint(2, 6)
        elif c == " ":
            x += 30
        else:
            x += espacio

    return lienzo


def limpiar_texto(texto: str) -> str:
    texto = texto.replace("\n", " ")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def dividir_oraciones(texto: str) -> list:
    return re.split(r"(?<=[.!?])\s+", limpiar_texto(texto))


def generar_resumen(texto: str) -> str:
    oraciones = [o.strip() for o in dividir_oraciones(texto) if len(o.strip()) > 30]
    return " ".join(oraciones[:3])


def generar_preguntas(texto: str) -> list:
    preguntas = []
    for o in dividir_oraciones(texto):
        o = o.strip()
        if len(o) < 35:
            continue

        if " es " in o:
            sujeto = o.split(" es ")[0]
            preguntas.append(f"¿Qué es {sujeto}?")
        elif " porque " in o:
            base = o.split(" porque ")[0]
            preguntas.append(f"¿Por qué {base}?")
        else:
            preguntas.append(f"Explica: {o[:60]}...")

    return preguntas[:8]


def generar_flashcards(texto: str) -> list:
    cards = []
    for o in dividir_oraciones(texto):
        o = o.strip()
        if len(o) < 35:
            continue

        if " es " in o:
            sujeto = o.split(" es ")[0]
            pregunta = f"¿Qué es {sujeto}?"
        elif " porque " in o:
            pregunta = f"¿Por qué {o.split(' porque ')[0]}?"
        else:
            pregunta = f"Explica: {o[:60]}..."

        cards.append((pregunta, o))

    return cards[:10]


def extraer_conceptos(texto: str) -> list:
    palabras = re.findall(r"\b[a-zA-ZáéíóúÁÉÍÓÚñÑ]{7,}\b", texto)
    unicas = []
    for p in palabras:
        if p.lower() not in [u.lower() for u in unicas]:
            unicas.append(p)
    return unicas[:12]


def generar_examen(texto: str) -> list:
    return generar_flashcards(texto)[:6]


def calificar(usuario: str, correcta: str) -> float:
    u = set(usuario.lower().split())
    c = set(correcta.lower().split())

    if not c:
        return 0.0

    coincidencias = u & c
    precision = len(coincidencias) / len(u) if u else 0
    cobertura = len(coincidencias) / len(c)

    return round(((precision + cobertura) / 2) * 10, 2)


def save_typography_image(texto: str, folder_tipografia: str, out_path: Path) -> Path:
    letras = cargar_tipografia(folder_tipografia)
    if not letras:
        raise RuntimeError("La carpeta tipografia está vacía o mal formada.")

    img = escribir_con_letra(texto, letras)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return out_path


def export_page_to_pdf(page: Page, output_path: str) -> str:
    doc = SimpleDocTemplate(output_path)
    styles = getSampleStyleSheet()
    story = []

    for element in page.elements:
        if isinstance(element, TextElement):
            for linea in element.text.split("\n"):
                story.append(Paragraph(linea, styles["Normal"]))
            story.append(Spacer(1, 8))

        elif isinstance(element, ImageElement):
            if element.image_path and Path(element.image_path).exists():
                img = RLImage(element.image_path, width=element.width, height=element.height)
                story.append(img)
                story.append(Spacer(1, 8))

    doc.build(story)
    return output_path