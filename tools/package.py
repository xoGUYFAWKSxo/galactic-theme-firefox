from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
ROOT = Path(__file__).resolve().parents[1]
import json
manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
name = "galactic-theme" if "theme" in manifest else "galactic-tab"
with ZipFile(ROOT / f"{name}.xpi", "w", ZIP_DEFLATED) as package:
    files = [ROOT / "manifest.json"]
    if "theme" in manifest:
        files += sorted((ROOT / "images").glob("*.png"))
    else:
        files += list(ROOT.glob("*.js")) + list(ROOT.glob("*.html")) + list(ROOT.glob("*.css"))
        files += [p for p in (ROOT / "assets").rglob("*") if p.is_file()]
    for path in files:
        package.write(path, path.relative_to(ROOT).as_posix())
print(f"Created {name}.xpi (unsigned)")
