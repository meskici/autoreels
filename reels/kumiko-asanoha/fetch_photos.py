#!/usr/bin/env python3
"""Download the product's real photos into assets/.

The Shopify CDN is reachable from a GitHub Actions runner but not from every
environment, so this is a separate step from the build: if it cannot fetch,
you find out here rather than three minutes into a render.
"""
import json, pathlib, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
HANDLE = sys.argv[1] if len(sys.argv) > 1 else "kumiko-asanoha"
CATALOG = ROOT / "examples" / "catalog" / f"{HANDLE}.json"
OUT = pathlib.Path(__file__).parent / "assets"

def main():
    product = json.loads(CATALOG.read_text(encoding="utf-8"))
    OUT.mkdir(exist_ok=True)
    manifest = []
    for img in product["images"]:
        url = img["url"]
        name = url.split("/")[-1].split("?")[0]
        dest = OUT / name
        if not dest.exists():
            req = urllib.request.Request(url, headers={"User-Agent": "autoreels/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            if len(data) < 2048:
                raise SystemExit(f"{name}: only {len(data)} bytes, refusing")
            dest.write_bytes(data)
        manifest.append({
            "file": name,
            "alt": img.get("altText", ""),
            "width": img.get("width"),
            "height": img.get("height"),
            "bytes": dest.stat().st_size,
        })
        print(f"  {name:<64} {dest.stat().st_size/1024:8.0f} KB")
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"\n{len(manifest)} photos in {OUT}")

if __name__ == "__main__":
    main()
