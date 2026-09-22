"""
Generador profesional de documentación técnica del Frontend
Inventario P.M.E.

Stack objetivo:
- HTML
- CSS
- JavaScript
- PHP
- AdminLTE
- Bootstrap
- Consumo de API REST

El script inspecciona el proyecto real y genera un documento DOCX
con estructura técnica, arquitectura, módulos, navegación, servicios,
endpoints, formularios, tablas, modales, dependencias y métricas.

Requisitos:
    pip install python-docx
"""

from __future__ import annotations

import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

FRONTEND_PATH = Path(r"F:\XAMPP\htdocs\frontend-inventario-pme")

OUTPUT_FILENAME = Path("Documentacion_Tecnica_Frontend_Inventario_PME.docx")

PROJECT_NAME = "Inventario P.M.E"
PROJECT_DESCRIPTION = (
    "Software para gestionar inventario para pequeñas y medianas empresas"
)

MAX_FILE_SIZE = 2_000_000

IGNORED_DIRECTORIES = {
    ".git",
    ".idea",
    ".vscode",
    "node_modules",
    ".next",
    "dist",
    "build",
    "vendor",
    "cache",
    "tmp",
    "temp",
    "__pycache__",
}

SOURCE_EXTENSIONS = {
    ".php",
    ".html",
    ".htm",
    ".js",
    ".css",
}

STYLE_EXTENSIONS = {".css"}

SCRIPT_EXTENSIONS = {".js"}

TEMPLATE_EXTENSIONS = {".php", ".html", ".htm"}

# Colores corporativos.
BLUE = RGBColor(31, 78, 121)
DARK_BLUE = RGBColor(20, 55, 90)
GRAY = RGBColor(89, 89, 89)
LIGHT_GRAY = RGBColor(242, 244, 247)
WHITE = RGBColor(255, 255, 255)
BLACK = RGBColor(0, 0, 0)


# ============================================================================
# MODELOS DE DATOS
# ============================================================================


@dataclass
class FileInfo:
    """Información técnica de un archivo del frontend."""

    path: Path
    relative_path: str
    extension: str
    size: int
    lines: int
    content: str = ""


@dataclass
class EndpointInfo:
    """Endpoint REST detectado en código frontend."""

    method: str
    endpoint: str
    file: str
    line: int


@dataclass
class ProjectAnalysis:
    """Resultado completo del análisis del frontend."""

    files: list[FileInfo] = field(default_factory=list)
    endpoints: list[EndpointInfo] = field(default_factory=list)
    dependencies: Counter = field(default_factory=Counter)
    modules: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    forms: list[dict] = field(default_factory=list)
    tables: list[dict] = field(default_factory=list)
    modals: list[dict] = field(default_factory=list)
    js_functions: list[dict] = field(default_factory=list)
    js_events: list[dict] = field(default_factory=list)
    php_includes: list[dict] = field(default_factory=list)
    css_files: list[str] = field(default_factory=list)
    js_files: list[str] = field(default_factory=list)
    template_files: list[str] = field(default_factory=list)
    metrics: dict[str, int] = field(default_factory=dict)


# ============================================================================
# UTILIDADES DE TEXTO
# ============================================================================


def normalize_path(path: Path) -> str:
    """Convierte una ruta a formato portable."""
    return str(path).replace("\\", "/")


def safe_read_text(path: Path) -> str:
    """Lee un archivo de texto evitando errores de codificación."""
    try:
        if path.stat().st_size > MAX_FILE_SIZE:
            return ""

        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except (OSError, UnicodeError):
        return ""


def line_number(content: str, position: int) -> int:
    """Obtiene el número de línea correspondiente a una posición."""
    return content.count("\n", 0, position) + 1


def unique_preserve_order(items: Iterable[str]) -> list[str]:
    """Elimina duplicados conservando el orden original."""
    return list(dict.fromkeys(items))


# ============================================================================
# ESCANEO DEL PROYECTO
# ============================================================================


def iter_source_files(root: Path) -> Iterable[Path]:
    """Recorre los archivos fuente excluyendo directorios no relevantes."""
    for current_root, dirs, files in os.walk(root):
        dirs[:] = [
            directory for directory in dirs if directory not in IGNORED_DIRECTORIES
        ]

        current_path = Path(current_root)

        for filename in files:
            path = current_path / filename

            if path.suffix.lower() in SOURCE_EXTENSIONS:
                yield path


def collect_files(root: Path) -> list[FileInfo]:
    """Recolecta información básica de todos los archivos fuente."""
    result = []

    for path in sorted(iter_source_files(root)):
        content = safe_read_text(path)
        relative = normalize_path(path.relative_to(root))

        result.append(
            FileInfo(
                path=path,
                relative_path=relative,
                extension=path.suffix.lower(),
                size=path.stat().st_size,
                lines=content.count("\n") + 1 if content else 0,
                content=content,
            )
        )

    return result


# ============================================================================
# DETECCIÓN DE ENDPOINTS
# ============================================================================


def detect_endpoints(file_info: FileInfo) -> list[EndpointInfo]:
    """
    Detecta endpoints usados desde JavaScript/PHP.

    Soporta patrones habituales:
    - fetch()
    - $.ajax()
    - $.get()
    - $.post()
    - $.put()
    - $.patch()
    - $.delete()
    """
    if file_info.extension not in {".js", ".php", ".html", ".htm"}:
        return []

    content = file_info.content

    patterns = [
        (
            "FETCH",
            re.compile(
                r"fetch\s*\(\s*['\"]([^'\"]+)['\"]",
                re.IGNORECASE,
            ),
        ),
        (
            "AJAX",
            re.compile(
                r"\$\.(?:ajax)\s*\(\s*['\"]([^'\"]+)['\"]",
                re.IGNORECASE,
            ),
        ),
        (
            "GET",
            re.compile(
                r"\$\.(?:get|getJSON)\s*\(\s*['\"]([^'\"]+)['\"]",
                re.IGNORECASE,
            ),
        ),
        (
            "POST",
            re.compile(
                r"\$\.post\s*\(\s*['\"]([^'\"]+)['\"]",
                re.IGNORECASE,
            ),
        ),
    ]

    endpoints = []

    for method, pattern in patterns:
        for match in pattern.finditer(content):
            endpoint = match.group(1).strip()

            if not endpoint:
                continue

            endpoints.append(
                EndpointInfo(
                    method=method,
                    endpoint=endpoint,
                    file=file_info.relative_path,
                    line=line_number(content, match.start()),
                )
            )

    return endpoints


# ============================================================================
# DETECCIÓN DE COMPONENTES
# ============================================================================


def detect_forms(file_info: FileInfo) -> list[dict]:
    """Detecta formularios HTML/PHP."""
    if file_info.extension not in TEMPLATE_EXTENSIONS:
        return []

    pattern = re.compile(
        r"<form\b([^>]*)>",
        re.IGNORECASE,
    )

    result = []

    for match in pattern.finditer(file_info.content):
        attributes = match.group(1)

        action = extract_attribute(attributes, "action")
        method = extract_attribute(attributes, "method") or "GET"
        form_id = extract_attribute(attributes, "id")
        form_name = extract_attribute(attributes, "name")

        result.append(
            {
                "file": file_info.relative_path,
                "id": form_id or "-",
                "name": form_name or "-",
                "action": action or "-",
                "method": method.upper(),
                "line": line_number(file_info.content, match.start()),
            }
        )

    return result


def detect_tables(file_info: FileInfo) -> list[dict]:
    """Detecta tablas HTML y sus identificadores."""
    if file_info.extension not in TEMPLATE_EXTENSIONS:
        return []

    pattern = re.compile(
        r"<table\b([^>]*)>",
        re.IGNORECASE,
    )

    result = []

    for match in pattern.finditer(file_info.content):
        attributes = match.group(1)

        result.append(
            {
                "file": file_info.relative_path,
                "id": extract_attribute(attributes, "id") or "-",
                "class": extract_attribute(attributes, "class") or "-",
                "line": line_number(file_info.content, match.start()),
            }
        )

    return result


def detect_modals(file_info: FileInfo) -> list[dict]:
    """Detecta modales Bootstrap/AdminLTE."""
    if file_info.extension not in TEMPLATE_EXTENSIONS:
        return []

    patterns = [
        re.compile(
            r'<div\b[^>]*class=["\'][^"\']*modal[^"\']*["\']',
            re.IGNORECASE,
        ),
        re.compile(
            r'<div\b[^>]*id=["\'][^"\']*modal[^"\']*["\']',
            re.IGNORECASE,
        ),
    ]

    result = []

    for pattern in patterns:
        for match in pattern.finditer(file_info.content):
            result.append(
                {
                    "file": file_info.relative_path,
                    "line": line_number(
                        file_info.content,
                        match.start(),
                    ),
                    "snippet": clean_snippet(match.group(0)),
                }
            )

    return result


def detect_js_functions(file_info: FileInfo) -> list[dict]:
    """Detecta funciones JavaScript tradicionales y flecha."""
    if file_info.extension != ".js":
        return []

    patterns = [
        re.compile(
            r"\bfunction\s+([A-Za-z_$][\w$]*)\s*\(",
        ),
        re.compile(
            r"\b(?:const|let|var)\s+"
            r"([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?"
            r"\([^)]*\)\s*=>",
        ),
    ]

    result = []

    for pattern in patterns:
        for match in pattern.finditer(file_info.content):
            result.append(
                {
                    "file": file_info.relative_path,
                    "name": match.group(1),
                    "line": line_number(
                        file_info.content,
                        match.start(),
                    ),
                }
            )

    return result


def detect_js_events(file_info: FileInfo) -> list[dict]:
    """Detecta eventos frecuentes de JavaScript/jQuery."""
    if file_info.extension != ".js":
        return []

    pattern = re.compile(
        r"\.(on|click|change|submit|keyup|keydown|"
        r"mouseenter|mouseleave)\s*\(",
        re.IGNORECASE,
    )

    result = []

    for match in pattern.finditer(file_info.content):
        result.append(
            {
                "file": file_info.relative_path,
                "event": match.group(1).lower(),
                "line": line_number(
                    file_info.content,
                    match.start(),
                ),
            }
        )

    return result


def detect_php_includes(file_info: FileInfo) -> list[dict]:
    """Detecta include, require, include_once y require_once."""
    if file_info.extension != ".php":
        return []

    pattern = re.compile(
        r"\b(include|require|include_once|require_once)"
        r"\s*\(?\s*['\"]([^'\"]+)['\"]",
        re.IGNORECASE,
    )

    result = []

    for match in pattern.finditer(file_info.content):
        result.append(
            {
                "file": file_info.relative_path,
                "type": match.group(1),
                "target": match.group(2),
                "line": line_number(
                    file_info.content,
                    match.start(),
                ),
            }
        )

    return result


def extract_attribute(attributes: str, name: str) -> str:
    """Extrae un atributo HTML."""
    pattern = re.compile(
        rf'\b{name}\s*=\s*["\']([^"\']*)["\']',
        re.IGNORECASE,
    )

    match = pattern.search(attributes)

    return match.group(1).strip() if match else ""


def clean_snippet(value: str) -> str:
    """Limpia espacios excesivos de un fragmento."""
    return re.sub(r"\s+", " ", value).strip()


# ============================================================================
# DEPENDENCIAS
# ============================================================================


def detect_dependencies(file_info: FileInfo) -> Counter:
    """Detecta librerías frontend comunes."""
    content = file_info.content.lower()
    dependencies = Counter()

    signatures = {
        "jQuery": ["jquery", "$("],
        "Bootstrap": ["bootstrap"],
        "AdminLTE": ["adminlte"],
        "DataTables": ["datatables", "datatable"],
        "Select2": ["select2"],
        "SweetAlert": ["sweetalert", "swal"],
        "Font Awesome": ["font-awesome", "fontawesome"],
        "Chart.js": ["chart.js", "new chart("],
        "Axios": ["axios"],
        "Moment.js": ["moment.js", "moment("],
    }

    for dependency, markers in signatures.items():
        if any(marker in content for marker in markers):
            dependencies[dependency] += 1

    return dependencies


# ============================================================================
# MÓDULOS
# ============================================================================


def classify_module(relative_path: str) -> str:
    """Clasifica archivos por módulo a partir de su ruta/nombre."""
    normalized = relative_path.lower()

    module_keywords = {
        "Dashboard": ["dashboard", "inicio", "home"],
        "Usuarios": ["user", "usuario", "usuarios"],
        "Roles y permisos": ["role", "rol", "permission", "permiso"],
        "Clientes": ["customer", "cliente", "clientes"],
        "Proveedores": ["supplier", "proveedor", "proveedores"],
        "Productos": ["product", "producto", "productos"],
        "Categorías": ["category", "categoria", "categoría"],
        "Inventario": [
            "inventory",
            "inventario",
            "stock",
            "existencia",
            "movimiento",
        ],
        "Compras": ["purchase", "purchases", "compra", "compras"],
        "Ventas": ["sale", "sales", "venta", "ventas"],
        "Facturación": [
            "invoice",
            "invoices",
            "factura",
            "facturacion",
            "facturación",
        ],
        "Reportes": ["report", "reporte", "reportes"],
        "Configuración": [
            "setting",
            "settings",
            "config",
            "configuracion",
            "configuración",
        ],
        "Auditoría": ["audit", "auditoria", "auditoría"],
    }

    for module, keywords in module_keywords.items():
        if any(keyword in normalized for keyword in keywords):
            return module

    return "Infraestructura / Otros"


# ============================================================================
# ANÁLISIS COMPLETO
# ============================================================================


def analyze_project(root: Path) -> ProjectAnalysis:
    """Ejecuta el análisis integral del frontend."""
    analysis = ProjectAnalysis()
    analysis.files = collect_files(root)

    for file_info in analysis.files:
        analysis.endpoints.extend(detect_endpoints(file_info))

        analysis.forms.extend(detect_forms(file_info))

        analysis.tables.extend(detect_tables(file_info))

        analysis.modals.extend(detect_modals(file_info))

        analysis.js_functions.extend(detect_js_functions(file_info))

        analysis.js_events.extend(detect_js_events(file_info))

        analysis.php_includes.extend(detect_php_includes(file_info))

        analysis.dependencies.update(detect_dependencies(file_info))

        module = classify_module(file_info.relative_path)
        analysis.modules[module].append(file_info.relative_path)

        if file_info.extension in STYLE_EXTENSIONS:
            analysis.css_files.append(file_info.relative_path)

        if file_info.extension in SCRIPT_EXTENSIONS:
            analysis.js_files.append(file_info.relative_path)

        if file_info.extension in TEMPLATE_EXTENSIONS:
            analysis.template_files.append(file_info.relative_path)

    analysis.metrics = {
        "total_files": len(analysis.files),
        "php_files": count_extensions(analysis.files, ".php"),
        "html_files": (
            count_extensions(analysis.files, ".html")
            + count_extensions(analysis.files, ".htm")
        ),
        "js_files": count_extensions(analysis.files, ".js"),
        "css_files": count_extensions(analysis.files, ".css"),
        "total_lines": sum(file_info.lines for file_info in analysis.files),
        "endpoints": len(unique_endpoints(analysis.endpoints)),
        "forms": len(analysis.forms),
        "tables": len(analysis.tables),
        "modals": len(unique_modals(analysis.modals)),
        "js_functions": len(analysis.js_functions),
        "js_events": len(analysis.js_events),
        "php_includes": len(analysis.php_includes),
    }

    return analysis


def count_extensions(
    files: list[FileInfo],
    extension: str,
) -> int:
    """Cuenta archivos por extensión."""
    return sum(1 for file_info in files if file_info.extension == extension)


def unique_endpoints(
    endpoints: list[EndpointInfo],
) -> list[EndpointInfo]:
    """Elimina endpoints duplicados."""
    seen = set()
    result = []

    for endpoint in endpoints:
        key = (
            endpoint.method,
            endpoint.endpoint,
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(endpoint)

    return result


def unique_modals(modals: list[dict]) -> list[dict]:
    """Elimina detecciones duplicadas de modales."""
    seen = set()
    result = []

    for modal in modals:
        key = (
            modal["file"],
            modal["line"],
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(modal)

    return result


# ============================================================================
# DOCUMENTO WORD
# ============================================================================


def configure_document(doc: Document) -> None:
    """Configura márgenes y estilos globales."""
    section = doc.sections[0]

    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.9)
    section.right_margin = Inches(0.9)

    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(10)

    for style_name in [
        "Title",
        "Heading 1",
        "Heading 2",
        "Heading 3",
    ]:
        style = doc.styles[style_name]
        style.font.name = "Arial"
        style.font.color.rgb = BLUE

    doc.core_properties.title = "Documentación Técnica del Frontend - Inventario P.M.E"
    doc.core_properties.subject = "Documentación técnica automática del frontend"
    doc.core_properties.author = "Inventario P.M.E"
    doc.core_properties.keywords = (
        "Frontend, PHP, JavaScript, AdminLTE, Bootstrap, API REST"
    )


def add_title_page(doc: Document) -> None:
    """Crea la portada profesional."""
    for _ in range(3):
        doc.add_paragraph()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    run = title.add_run("DOCUMENTACIÓN TÉCNICA DEL FRONTEND")
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(24)
    run.font.color.rgb = BLUE

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER

    run = subtitle.add_run(PROJECT_NAME)
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(18)
    run.font.color.rgb = DARK_BLUE

    description = doc.add_paragraph()
    description.alignment = WD_ALIGN_PARAGRAPH.CENTER

    run = description.add_run(PROJECT_DESCRIPTION)
    run.italic = True
    run.font.name = "Arial"
    run.font.size = Pt(12)
    run.font.color.rgb = GRAY

    doc.add_paragraph()
    doc.add_paragraph()

    stack = doc.add_paragraph()
    stack.alignment = WD_ALIGN_PARAGRAPH.CENTER
    stack.add_run("HTML • CSS • JavaScript • PHP • AdminLTE • Bootstrap").bold = True

    doc.add_paragraph()
    doc.add_paragraph()

    generated = doc.add_paragraph()
    generated.alignment = WD_ALIGN_PARAGRAPH.CENTER
    generated.add_run(
        "Documento generado automáticamente a partir del código fuente."
    ).italic = True

    doc.add_page_break()


def add_heading(
    doc: Document,
    text: str,
    level: int = 1,
) -> None:
    """Agrega encabezado con formato corporativo."""
    heading = doc.add_heading(text, level=level)
    heading.style.font.color.rgb = BLUE


def add_paragraph(
    doc: Document,
    text: str,
    bold_prefix: str | None = None,
) -> None:
    """Agrega párrafo con soporte para prefijo destacado."""
    paragraph = doc.add_paragraph()

    if bold_prefix and text.startswith(bold_prefix):
        prefix = paragraph.add_run(bold_prefix)
        prefix.bold = True
        paragraph.add_run(text[len(bold_prefix) :])
    else:
        paragraph.add_run(text)


def add_table(
    doc: Document,
    headers: list[str],
    rows: list[list[str]],
) -> None:
    """Crea una tabla profesional."""
    table = doc.add_table(
        rows=1,
        cols=len(headers),
    )

    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"

    header_cells = table.rows[0].cells

    for index, header in enumerate(headers):
        cell = header_cells[index]
        cell.text = header
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True
                run.font.color.rgb = WHITE

        shade = OxmlElement("w:shd")
        shade.set(qn("w:fill"), "1F4E79")
        cell._tc.get_or_add_tcPr().append(shade)

    for row in rows:
        cells = table.add_row().cells

        for index, value in enumerate(row):
            cells[index].text = str(value)
            cells[index].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def add_bullets(
    doc: Document,
    items: Iterable[str],
) -> None:
    """Agrega lista de viñetas."""
    for item in items:
        paragraph = doc.add_paragraph(
            style="List Bullet",
        )
        paragraph.add_run(item)


# ============================================================================
# SECCIONES DEL DOCUMENTO
# ============================================================================


def build_document(
    analysis: ProjectAnalysis,
) -> Document:
    """Construye el documento técnico completo."""
    doc = Document()

    configure_document(doc)
    add_title_page(doc)

    add_section_introduction(doc)
    add_section_objectives(doc)
    add_section_scope(doc)
    add_section_architecture(doc)
    add_section_technology(doc)
    add_section_metrics(doc, analysis)
    add_section_structure(doc, analysis)
    add_section_modules(doc, analysis)
    add_section_navigation(doc)
    add_section_components(doc, analysis)
    add_section_services(doc, analysis)
    add_section_api(doc, analysis)
    add_section_authentication(doc, analysis)
    add_section_security(doc)
    add_section_forms(doc, analysis)
    add_section_tables(doc, analysis)
    add_section_modals(doc, analysis)
    add_section_dependencies(doc, analysis)
    add_section_php(doc, analysis)
    add_section_js(doc, analysis)
    add_section_css(doc, analysis)
    add_section_quality(doc, analysis)
    add_section_maintenance(doc)
    add_section_limitations(doc, analysis)
    add_section_conclusions(doc, analysis)

    return doc


def add_section_introduction(doc: Document) -> None:
    add_heading(doc, "1. Introducción")

    add_paragraph(
        doc,
        (
            f"Este documento presenta la documentación técnica del frontend "
            f"del sistema {PROJECT_NAME}. Su objetivo es describir la "
            f"estructura real del código construido, sus componentes, "
            f"módulos funcionales, mecanismos de navegación, integración "
            f"con servicios REST y elementos de interfaz detectados "
            f"directamente en el repositorio."
        ),
    )

    add_paragraph(
        doc,
        (
            "La documentación se genera mediante análisis automatizado "
            "del código fuente disponible. Por esta razón, los elementos "
            "que no puedan ser identificados de manera objetiva se "
            "presentan como no detectados y no como funcionalidades "
            "supuestas."
        ),
    )


def add_section_objectives(doc: Document) -> None:
    add_heading(doc, "2. Objetivos del Frontend")

    add_bullets(
        doc,
        [
            "Proporcionar una interfaz web organizada y usable.",
            "Facilitar la gestión visual de los módulos del sistema.",
            "Consumir de forma estructurada los servicios REST del backend.",
            "Aplicar controles de autenticación y autorización.",
            "Centralizar componentes y patrones reutilizables.",
            "Facilitar el mantenimiento y crecimiento futuro del sistema.",
        ],
    )


def add_section_scope(doc: Document) -> None:
    add_heading(doc, "3. Alcance")

    add_paragraph(
        doc,
        (
            "El análisis cubre los archivos fuente HTML, PHP, JavaScript "
            "y CSS encontrados dentro del directorio configurado. "
            "Se excluyen directorios generados, dependencias de terceros "
            "y artefactos que normalmente no forman parte del código "
            "fuente funcional."
        ),
    )


def add_section_architecture(doc: Document) -> None:
    add_heading(doc, "4. Arquitectura General")

    add_paragraph(
        doc,
        (
            "El frontend funciona como capa de presentación del sistema. "
            "Su responsabilidad principal es renderizar las vistas, "
            "capturar las interacciones del usuario, ejecutar validaciones "
            "de interfaz y comunicarse con el backend mediante solicitudes "
            "HTTP/HTTPS."
        ),
    )

    architecture = [
        ["Capa", "Responsabilidad"],
        ["Presentación", "HTML, PHP, AdminLTE y Bootstrap."],
        ["Interacción", "JavaScript, jQuery y eventos de interfaz."],
        ["Comunicación", "Servicios HTTP y consumo de API REST."],
        ["Seguridad", "Autenticación, sesión y permisos."],
        ["Backend", "Django REST Framework."],
        ["Persistencia", "Base de datos administrada por el backend."],
    ]

    add_table(
        doc,
        architecture[0],
        architecture[1:],
    )


def add_section_technology(doc: Document) -> None:
    add_heading(doc, "5. Tecnologías y Herramientas")

    rows = [
        ["Tecnología", "Uso"],
        ["HTML", "Estructura semántica de las vistas."],
        ["PHP", "Motor de plantillas y composición de páginas."],
        ["CSS", "Presentación y estilos personalizados."],
        ["JavaScript", "Interactividad y lógica del cliente."],
        ["AdminLTE", "Panel administrativo y componentes visuales."],
        ["Bootstrap", "Sistema de estilos y componentes responsive."],
        ["Django REST Framework", "Backend y API REST consumida."],
    ]

    add_table(doc, rows[0], rows[1:])


def add_section_metrics(
    doc: Document,
    analysis: ProjectAnalysis,
) -> None:
    add_heading(doc, "6. Métricas del Código Analizado")

    metrics = analysis.metrics

    rows = [
        ["Métrica", "Cantidad"],
        ["Archivos analizados", str(metrics["total_files"])],
        ["Archivos PHP", str(metrics["php_files"])],
        ["Archivos HTML", str(metrics["html_files"])],
        ["Archivos JavaScript", str(metrics["js_files"])],
        ["Archivos CSS", str(metrics["css_files"])],
        ["Líneas aproximadas", str(metrics["total_lines"])],
        ["Endpoints detectados", str(metrics["endpoints"])],
        ["Formularios detectados", str(metrics["forms"])],
        ["Tablas detectadas", str(metrics["tables"])],
        ["Modales detectados", str(metrics["modals"])],
        ["Funciones JavaScript", str(metrics["js_functions"])],
        ["Eventos JavaScript", str(metrics["js_events"])],
        ["Includes PHP", str(metrics["php_includes"])],
    ]

    add_table(doc, rows[0], rows[1:])


def add_section_structure(
    doc: Document,
    analysis: ProjectAnalysis,
) -> None:
    add_heading(doc, "7. Estructura del Proyecto")

    add_paragraph(
        doc,
        (
            "La siguiente relación corresponde exclusivamente a los "
            "archivos fuente detectados durante el análisis."
        ),
    )

    rows = [
        ["Archivo", "Tipo", "Líneas", "Tamaño"],
    ]

    for file_info in analysis.files:
        size_kb = file_info.size / 1024

        rows.append(
            [
                file_info.relative_path,
                file_info.extension.upper(),
                str(file_info.lines),
                f"{size_kb:.1f} KB",
            ]
        )

    add_table(doc, rows[0], rows[1:])


def add_section_modules(
    doc: Document,
    analysis: ProjectAnalysis,
) -> None:
    add_heading(doc, "8. Módulos Funcionales Detectados")

    rows = [
        ["Módulo", "Archivos detectados"],
    ]

    for module, files in sorted(analysis.modules.items()):
        rows.append(
            [
                module,
                str(len(files)),
            ]
        )

    add_table(doc, rows[0], rows[1:])

    add_paragraph(
        doc,
        (
            "La clasificación de módulos se realiza mediante patrones "
            "de nombres y rutas. Por lo tanto, debe interpretarse como "
            "una clasificación técnica automática y no como una "
            "validación funcional del negocio."
        ),
    )


def add_section_navigation(doc: Document) -> None:
    add_heading(doc, "9. Navegación Funcional")

    add_paragraph(
        doc,
        (
            "La navegación del sistema debe organizarse alrededor de los "
            "módulos disponibles y de las acciones permitidas para cada "
            "perfil. El mapa de navegación del proyecto contempla áreas "
            "como dashboard, productos, clientes, proveedores, ventas, "
            "compras, inventario, reportes, administración y configuración."
        ),
    )

    add_bullets(
        doc,
        [
            "Inicio / Dashboard",
            "Usuarios",
            "Roles y permisos",
            "Clientes",
            "Proveedores",
            "Productos",
            "Categorías",
            "Inventario",
            "Compras",
            "Ventas",
            "Facturación",
            "Reportes",
            "Configuración",
            "Auditoría",
        ],
    )


def add_section_components(
    doc: Document,
    analysis: ProjectAnalysis,
) -> None:
    add_heading(doc, "10. Componentes de Interfaz Detectados")

    add_heading(doc, "10.1 Formularios", 2)

    if analysis.forms:
        rows = [
            [
                "Archivo",
                "ID",
                "Nombre",
                "Método",
                "Action",
                "Línea",
            ]
        ]

        for form in analysis.forms:
            rows.append(
                [
                    form["file"],
                    form["id"],
                    form["name"],
                    form["method"],
                    form["action"],
                    str(form["line"]),
                ]
            )

        add_table(doc, rows[0], rows[1:])
    else:
        add_paragraph(doc, "No se detectaron formularios.")

    add_heading(doc, "10.2 Tablas", 2)

    if analysis.tables:
        rows = [["Archivo", "ID", "Clase", "Línea"]]

        for table in analysis.tables:
            rows.append(
                [
                    table["file"],
                    table["id"],
                    table["class"],
                    str(table["line"]),
                ]
            )

        add_table(doc, rows[0], rows[1:])
    else:
        add_paragraph(doc, "No se detectaron tablas.")

    add_heading(doc, "10.3 Modales", 2)

    modals = unique_modals(analysis.modals)

    if modals:
        rows = [["Archivo", "Línea", "Detección"]]

        for modal in modals:
            rows.append(
                [
                    modal["file"],
                    str(modal["line"]),
                    modal["snippet"],
                ]
            )

        add_table(doc, rows[0], rows[1:])
    else:
        add_paragraph(doc, "No se detectaron modales.")


def add_section_services(
    doc: Document,
    analysis: ProjectAnalysis,
) -> None:
    add_heading(doc, "11. Servicios y Comunicación")

    add_paragraph(
        doc,
        (
            "Los archivos JavaScript que contienen llamadas HTTP o "
            "funciones de integración representan la capa de comunicación "
            "entre la interfaz y la API. La detección automática permite "
            "identificar puntos de integración, pero no sustituye una "
            "revisión funcional de cada servicio."
        ),
    )

    if analysis.endpoints:
        add_paragraph(
            doc,
            "Archivos con integración HTTP detectada:",
        )

        files = unique_preserve_order(endpoint.file for endpoint in analysis.endpoints)

        add_bullets(doc, files)
    else:
        add_paragraph(
            doc,
            "No se detectaron llamadas HTTP mediante los patrones configurados.",
        )


def add_section_api(
    doc: Document,
    analysis: ProjectAnalysis,
) -> None:
    add_heading(doc, "12. Integración con la API REST")

    endpoints = unique_endpoints(analysis.endpoints)

    if not endpoints:
        add_paragraph(
            doc,
            "No se detectaron endpoints mediante los patrones automatizados.",
        )
        return

    rows = [
        [
            "Método",
            "Endpoint",
            "Archivo",
            "Línea",
        ]
    ]

    for endpoint in endpoints:
        rows.append(
            [
                endpoint.method,
                endpoint.endpoint,
                endpoint.file,
                str(endpoint.line),
            ]
        )

    add_table(doc, rows[0], rows[1:])

    add_paragraph(
        doc,
        (
            "Los endpoints anteriores fueron identificados mediante "
            "patrones estáticos. Si una URL se construye dinámicamente "
            "mediante variables, funciones o configuración externa, "
            "puede no aparecer en esta tabla."
        ),
    )


def add_section_authentication(
    doc: Document,
    analysis: ProjectAnalysis,
) -> None:
    add_heading(doc, "13. Autenticación y Gestión de Sesión")

    add_paragraph(
        doc,
        (
            "El frontend debe actuar como consumidor de los mecanismos "
            "de autenticación definidos por el backend. En el sistema "
            "Inventario P.M.E, la capa de seguridad contempla autenticación "
            "y un contexto de seguridad para determinar las capacidades "
            "del usuario."
        ),
    )

    auth_keywords = [
        "login",
        "logout",
        "token",
        "jwt",
        "session",
        "auth",
        "permission",
        "role",
    ]

    matches = []

    for file_info in analysis.files:
        content = file_info.content.lower()

        if any(keyword in content for keyword in auth_keywords):
            matches.append(file_info.relative_path)

    if matches:
        add_paragraph(
            doc,
            "Archivos donde se detectaron términos relacionados:",
        )
        add_bullets(
            doc,
            unique_preserve_order(matches),
        )
    else:
        add_paragraph(
            doc,
            "No se detectaron referencias explícitas mediante los "
            "términos configurados.",
        )


def add_section_security(doc: Document) -> None:
    add_heading(doc, "14. Seguridad del Frontend")

    add_bullets(
        doc,
        [
            "No almacenar secretos del backend en el código cliente.",
            "Validar permisos tanto en frontend como en backend.",
            "No confiar exclusivamente en controles visuales.",
            "Utilizar HTTPS en entornos productivos.",
            "Evitar insertar contenido no confiable directamente en HTML.",
            "Validar datos antes de enviarlos a la API.",
            "Gestionar correctamente expiración y cierre de sesión.",
            "Aplicar protección CSRF cuando el mecanismo de autenticación "
            "y la arquitectura lo requieran.",
        ],
    )


def add_section_forms(
    doc: Document,
    analysis: ProjectAnalysis,
) -> None:
    add_heading(doc, "15. Formularios y Validación")

    add_paragraph(
        doc,
        (
            "Los formularios constituyen el principal mecanismo de captura "
            "de información. El análisis identifica formularios HTML/PHP, "
            "pero las reglas de validación específicas pueden encontrarse "
            "en JavaScript o en el backend y deben mantenerse sincronizadas."
        ),
    )

    if analysis.forms:
        methods = Counter(form["method"] for form in analysis.forms)

        rows = [
            ["Método", "Cantidad"],
        ]

        for method, count in sorted(methods.items()):
            rows.append([method, str(count)])

        add_table(doc, rows[0], rows[1:])


def add_section_tables(
    doc: Document,
    analysis: ProjectAnalysis,
) -> None:
    add_heading(doc, "16. Tablas y Gestión de Datos")

    add_paragraph(
        doc,
        (
            "Las tablas permiten presentar información operacional del "
            "sistema. Cuando se utiliza DataTables u otra librería, la "
            "configuración específica puede encontrarse en los archivos "
            "JavaScript correspondientes."
        ),
    )

    if analysis.tables:
        add_bullets(
            doc,
            unique_preserve_order(table["file"] for table in analysis.tables),
        )


def add_section_modals(
    doc: Document,
    analysis: ProjectAnalysis,
) -> None:
    add_heading(doc, "17. Modales e Interacciones")

    modals = unique_modals(analysis.modals)

    if modals:
        add_paragraph(
            doc,
            (
                f"Se detectaron {len(modals)} posibles componentes "
                "modales mediante clases o identificadores asociados "
                "a Bootstrap/AdminLTE."
            ),
        )
    else:
        add_paragraph(
            doc,
            "No se detectaron componentes modales.",
        )


def add_section_dependencies(
    doc: Document,
    analysis: ProjectAnalysis,
) -> None:
    add_heading(doc, "18. Dependencias Frontend")

    if not analysis.dependencies:
        add_paragraph(
            doc,
            "No se detectaron librerías mediante las firmas configuradas.",
        )
        return

    rows = [
        ["Librería", "Archivos donde aparece"],
    ]

    for dependency, count in sorted(analysis.dependencies.items()):
        rows.append(
            [
                dependency,
                str(count),
            ]
        )

    add_table(doc, rows[0], rows[1:])


def add_section_php(
    doc: Document,
    analysis: ProjectAnalysis,
) -> None:
    add_heading(doc, "19. Arquitectura PHP y Plantillas")

    add_paragraph(
        doc,
        (
            "Los archivos PHP funcionan como parte de la capa de "
            "presentación y composición de las vistas. Los includes y "
            "requires permiten reutilizar elementos comunes como "
            "cabeceras, menús, barras laterales, pie de página y "
            "configuración."
        ),
    )

    if analysis.php_includes:
        rows = [
            [
                "Archivo",
                "Tipo",
                "Recurso",
                "Línea",
            ]
        ]

        for include in analysis.php_includes:
            rows.append(
                [
                    include["file"],
                    include["type"],
                    include["target"],
                    str(include["line"]),
                ]
            )

        add_table(doc, rows[0], rows[1:])


def add_section_js(
    doc: Document,
    analysis: ProjectAnalysis,
) -> None:
    add_heading(doc, "20. JavaScript e Interactividad")

    if analysis.js_functions:
        add_heading(doc, "20.1 Funciones detectadas", 2)

        rows = [
            ["Archivo", "Función", "Línea"],
        ]

        for function in analysis.js_functions:
            rows.append(
                [
                    function["file"],
                    function["name"],
                    str(function["line"]),
                ]
            )

        add_table(doc, rows[0], rows[1:])

    if analysis.js_events:
        add_heading(doc, "20.2 Eventos detectados", 2)

        event_counts = Counter(event["event"] for event in analysis.js_events)

        rows = [
            ["Evento", "Cantidad"],
        ]

        for event, count in sorted(event_counts.items()):
            rows.append(
                [
                    event,
                    str(count),
                ]
            )

        add_table(doc, rows[0], rows[1:])


def add_section_css(
    doc: Document,
    analysis: ProjectAnalysis,
) -> None:
    add_heading(doc, "21. CSS y Presentación Visual")

    if analysis.css_files:
        add_paragraph(
            doc,
            "Archivos CSS detectados:",
        )
        add_bullets(
            doc,
            analysis.css_files,
        )
    else:
        add_paragraph(
            doc,
            "No se detectaron archivos CSS.",
        )


def add_section_quality(
    doc: Document,
    analysis: ProjectAnalysis,
) -> None:
    add_heading(doc, "22. Calidad y Mantenibilidad")

    add_paragraph(
        doc,
        (
            "La presente sección no constituye una auditoría estática "
            "completa. Resume indicadores obtenidos del análisis "
            "automatizado y establece aspectos que deben verificarse "
            "durante una revisión técnica."
        ),
    )

    checks = [
        "Separación entre presentación y lógica JavaScript.",
        "Centralización de llamadas a la API.",
        "Reutilización de componentes PHP.",
        "Uso consistente de nombres y rutas.",
        "Validación de formularios.",
        "Manejo uniforme de errores.",
        "Control de autenticación y permisos.",
        "Ausencia de secretos dentro del código cliente.",
        "Compatibilidad responsive.",
        "Manejo correcto de estados de carga y vacío.",
    ]

    add_bullets(doc, checks)


def add_section_maintenance(doc: Document) -> None:
    add_heading(doc, "23. Mantenimiento y Escalabilidad")

    add_paragraph(
        doc,
        (
            "La estructura del frontend debe mantenerse modular para "
            "permitir incorporar nuevos módulos sin duplicar lógica. "
            "Los componentes visuales reutilizables, servicios de API, "
            "configuración y mecanismos de seguridad deberían permanecer "
            "centralizados siempre que la arquitectura existente lo permita."
        ),
    )

    add_bullets(
        doc,
        [
            "Mantener una convención uniforme de nombres.",
            "Evitar duplicación de llamadas HTTP.",
            "Centralizar configuración de API.",
            "Separar lógica de negocio de manipulación del DOM.",
            "Reutilizar componentes de interfaz.",
            "Documentar cambios importantes.",
            "Validar compatibilidad antes de modificar dependencias.",
        ],
    )


def add_section_limitations(
    doc: Document,
    analysis: ProjectAnalysis,
) -> None:
    add_heading(doc, "24. Limitaciones del Análisis Automático")

    add_bullets(
        doc,
        [
            "No se interpreta completamente la lógica de negocio.",
            "No se ejecuta la aplicación durante el análisis.",
            "No se validan endpoints contra un servidor real.",
            "Las URLs construidas dinámicamente pueden no detectarse.",
            "Las funcionalidades pueden depender de archivos externos.",
            "La clasificación de módulos se basa en nombres y rutas.",
            "La detección de librerías se basa en firmas de texto.",
        ],
    )


def add_section_conclusions(
    doc: Document,
    analysis: ProjectAnalysis,
) -> None:
    add_heading(doc, "25. Conclusiones")

    add_paragraph(
        doc,
        (
            f"El análisis documentó {analysis.metrics['total_files']} "
            f"archivos fuente y aproximadamente "
            f"{analysis.metrics['total_lines']} líneas de código. "
            "El resultado proporciona una visión técnica del estado "
            "actual del frontend y sirve como base para mantenimiento, "
            "auditoría, transferencia de conocimiento y evolución "
            "del sistema."
        ),
    )

    add_paragraph(
        doc,
        (
            "Esta documentación debe considerarse una fotografía "
            "técnica del código existente en el momento de su generación. "
            "Debe regenerarse después de cambios estructurales "
            "significativos."
        ),
    )


# ============================================================================
# EJECUCIÓN
# ============================================================================


def create_document() -> None:
    """Ejecuta el análisis y genera el documento DOCX."""
    if not FRONTEND_PATH.exists():
        raise FileNotFoundError(f"No existe el frontend: {FRONTEND_PATH}")

    if not FRONTEND_PATH.is_dir():
        raise NotADirectoryError(f"La ruta no es un directorio: {FRONTEND_PATH}")

    print("Analizando frontend...")
    analysis = analyze_project(FRONTEND_PATH)

    print(f"Archivos encontrados: {analysis.metrics['total_files']}")

    print("Generando documentación...")
    document = build_document(analysis)

    document.save(OUTPUT_FILENAME)

    print()
    print("==============================================")
    print("DOCUMENTACIÓN GENERADA CORRECTAMENTE")
    print("==============================================")
    print(f"Archivo: {OUTPUT_FILENAME.resolve()}")
    print(f"Archivos analizados: {analysis.metrics['total_files']}")
    print(f"Líneas aproximadas: {analysis.metrics['total_lines']}")
    print(f"Endpoints detectados: {analysis.metrics['endpoints']}")
    print(f"Formularios detectados: {analysis.metrics['forms']}")
    print(f"Tablas detectadas: {analysis.metrics['tables']}")
    print(f"Modales detectados: {analysis.metrics['modals']}")
    print("==============================================")


if __name__ == "__main__":
    try:
        create_document()
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"ERROR: {exc}")
    except PermissionError as exc:
        print(f"ERROR DE PERMISOS: {exc}")
    except OSError as exc:
        print(f"ERROR DEL SISTEMA: {exc}")
