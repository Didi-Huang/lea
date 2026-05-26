"""Internationalization support for LabExpAssistant."""

import json
from pathlib import Path

# ── 常量 ──────────────────────────────────────────────
LOCALES_DIR: Path = Path(__file__).resolve().parent.parent / "locales"
DPI_MIN: int = 100
DPI_MAX: int = 400
DPI_DEFAULT: int = 250
TAB_ORDER: list[str] = [
    "tab.project",
    "tab.data",
    "tab.snippets",
    "tab.convertor",
    "tab.cache_cleaner",
    "tab.settings",
]


# ── 翻译支持 ─────────────────────────────────────────
_translations: dict[str, dict[str, str]] = {}
_current_lang: str = "en"


def load_translations() -> None:
    """加载所有语言包。"""
    _translations.clear()
    for lang in ("en", "zh_CN", "ja"):
        path = LOCALES_DIR / f"{lang}.json"
        if path.exists():
            _translations[lang] = json.loads(path.read_text("utf-8"))


def tr(key: str) -> str:
    """国际化翻译。"""
    return _translations.get(_current_lang, {}).get(key, key)


def set_language(lang: str) -> None:
    """切换全局语言。"""
    global _current_lang
    if lang in ("en", "zh_CN", "ja"):
        _current_lang = lang


# ── 主窗口 ────────────────────────────────────────────
