import csv, sys, re, json
sys.path.insert(0, "scripts")
import pymupdf
rows = [r for r in csv.DictReader(open("manifest.csv", encoding="utf-8-sig")) if r["download_status"] == "downloaded"]
seen = set(); out = []
for r in rows:
    p = r["local_path"]
    if p in seen: continue
    seen.add(p)
    doc = pymupdf.open(p)
    for i, pg in enumerate(doc):
        W = pg.rect.width
        lines = [l for b in pg.get_text("dict")["blocks"] if b["type"] == 0 for l in b["lines"] if "".join(s["text"] for s in l["spans"]).strip()]
        right = [l for l in lines if l["bbox"][0] > W * 0.45 and (l["bbox"][2] - l["bbox"][0]) > 60]
        left_narrow = [l for l in lines if l["bbox"][0] < W * 0.2 and l["bbox"][2] < W * 0.55 and (l["bbox"][2] - l["bbox"][0]) > 60]
        try:
            tabs = pg.find_tables().tables
        except Exception:
            tabs = []
        imgs = [b for b in pg.get_text("dict")["blocks"] if b["type"] == 1 and (b["bbox"][2]-b["bbox"][0]) * (b["bbox"][3]-b["bbox"][1]) > 0.15 * W * pg.rect.height]
        two_col = len(right) >= 8 and len(left_narrow) >= 8
        if two_col or tabs:
            out.append({"pdf": p, "page": i + 1, "two_col": two_col, "right": len(right), "left_narrow": len(left_narrow),
                        "tables": [(t.row_count, t.col_count) for t in tabs], "big_images": len(imgs)})
json.dump(out, open("cache/layout_scan.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for o in out: print(o)
