"""Make the pipeline scripts importable in tests (their file names start with a digit)."""
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_script(name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def ex():
    return load_script("03_excerpt")


@pytest.fixture(scope="session")
def checklist(ex):
    return ex.Checklist(ex.ROOT / "reference" / "checklist_aopk.csv")


@pytest.fixture
def excerpt(ex, checklist, tmp_path):
    """Run the excerptor on a Markdown snippet → Article (locs, occs with flags/remarks still as lists)."""
    def run(md: str, title: str = "Exkurze", section: str = "EXKURZE"):
        path = tmp_path / "ZMSPCBS_2099-99-1-9.md"
        path.write_text(md, encoding="utf-8")
        meta = {"local_path": "pdf/99/ZMSPCBS_2099-99-1-9.pdf", "citation": "test", "section": section,
                "title": title, "issue_no": "99", "supplement": "", "pages": "1–9"}
        return ex.Excerptor(path, meta, checklist).run()
    return run


def numbered_localities(n: int) -> str:
    """'## Seznam lokalit' with n minimal numbered entries (enough for species lists to resolve their numbers)."""
    return "## Seznam lokalit\n\n" + "\n\n".join(f"{k}. 6370c, Obec{k}: les." for k in range(1, n + 1)) + "\n\n"
