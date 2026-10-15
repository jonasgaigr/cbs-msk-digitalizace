"""QA for step 2: compare the word sequence of each Markdown file with its PDF text layer.

    python scripts/qa_transcription.py [--only SUBSTR ...]

PDF side: PyMuPDF plain text minus running-header lines, soft hyphens rejoined; words inside ruled
tables are compared as a multiset (cell order may legitimately differ, e.g. sideways tables).
MD side: front matter, HTML comments, vision-transcribed blocks and Markdown markup removed.
Prints every difference (difflib opcodes on word tokens) so omissions/duplications are visible.
"""
from __future__ import annotations

import argparse
import difflib
import re
import unicodedata
from collections import Counter
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import MD_DIR, ROOT  # noqa: E402

import importlib.util

_spec = importlib.util.spec_from_file_location("transcribe", Path(__file__).with_name("02_transcribe.py"))
T = importlib.util.module_from_spec(_spec)
sys.modules["transcribe"] = T
_spec.loader.exec_module(T)


def _words(text: str) -> list[str]:
    text = re.sub("\xad\\s*\n\\s*", "", text).replace("\xad", "")
    return text.replace("\xa0", " ").split()


def pdf_words(pdf: Path, authors: str = "") -> tuple[list[str], Counter]:
    """Running-text words in order; words printed inside ruled tables as a multiset."""
    words, table_words = [], Counter()
    T.DOC["authors"] = set(re.findall(r"[^\W\d_]+", authors))   # byline decoding takes author capitalisation
    with pymupdf.open(pdf) as doc:
        for pg in doc:
            body, _, _ = T.page_lines(pg)
            words += _words("\n".join(ln.text for ln in body if not ln.table))
            lines = [l for b in pg.get_text("dict")["blocks"] if b["type"] == 0 for l in b["lines"]]
            for tab in (ln for ln in body if ln.table):
                rect = (tab.x0, tab.y0, tab.x1, tab.y1)
                inside = ["".join(s["text"] for s in l["spans"] if T._inside(s["bbox"], rect)) for l in lines]
                table_words.update(_words("\n".join(t for t in inside if t.strip())))
    return words, table_words


def _strip_md(text: str) -> str:
    text = re.sub(r"</?sup>", "", text)
    text = re.sub(r"^#{1,6} ", "", text, flags=re.M)
    text = text.replace("\\*", "\x00").replace("*", "").replace("\x00", "*")
    return re.sub(r"\\([.#>+\-_`|])", r"\1", text)


def md_words(md: Path) -> tuple[list[str], Counter]:
    text = md.read_text(encoding="utf-8")
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
    text = re.sub(r"<!-- begin: image.*?<!-- end: image transcription -->", " ", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    table_lines = [l for l in text.splitlines() if l.startswith("|")]
    other = "\n".join(l for l in text.splitlines() if not l.startswith("|"))
    cells = [c for l in table_lines if not re.fullmatch(r"\|(---\|)+", l)
             for c in re.split(r"(?<!\\)\|", l)]
    return _strip_md(other).split(), Counter(_strip_md(" ".join(cells)).split())


def compare(pdf: Path, md: Path) -> list[str]:
    m = re.search(r'^authors: "(.*?)"', md.read_text(encoding="utf-8"), re.M)
    (a, ta), (b, tb) = pdf_words(pdf, m.group(1) if m else ""), md_words(md)
    a = [unicodedata.normalize("NFC", w) for w in a]
    out = []
    missing, extra = ta - tb, tb - ta
    if missing or extra:
        out.append(f"table words: missing in MD {dict(missing)} | extra in MD {dict(extra)}")
    # hard hyphen / dash at line end is joined without a space in MD: compare on a joined stream
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        pa, pb = " ".join(a[i1:i2]), " ".join(b[j1:j2])
        if pa.replace(" ", "") == pb.replace(" ", ""):
            continue  # only whitespace differs (line-end hyphen/dash joins)
        if pa.replace(" ", "").replace("-", "") == pb.replace(" ", "").replace("-", ""):
            continue  # line-end '-' hyphenation rejoined (hard-hyphen PDFs)
        out.append(f"{op}: PDF «{pa[:120]}» → MD «{pb[:120]}»")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()
    for md in sorted(MD_DIR.rglob("*.md")):
        if args.only and not any(s in md.name for s in args.only):
            continue
        m = re.search(r'^source_file: "(.+?)"', md.read_text(encoding="utf-8"), re.M)
        diffs = compare(ROOT / m.group(1), md)
        print(f"{md.relative_to(ROOT).as_posix()}: {len(diffs)} differences")
        for d in diffs[:40]:
            print("   ", d)


if __name__ == "__main__":
    main()
