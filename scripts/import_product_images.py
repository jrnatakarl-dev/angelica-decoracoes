"""Optimize authorized product photos and register them in the catalog."""
from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path

from PIL import Image, ImageCms, ImageOps

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "public" / "assets" / "data" / "catalog.json"
OUTPUT_DIR = ROOT / "public" / "assets" / "images" / "products"
MAX_EDGE = 2000


def optimize_image(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Imagem não encontrada: {source}")

    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        image.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
        profile = image.info.get("icc_profile")
        alpha = image.getchannel("A") if "A" in image.getbands() else None
        if profile:
            try:
                image = ImageCms.profileToProfile(
                    image.convert("RGB"),
                    ImageCms.ImageCmsProfile(io.BytesIO(profile)),
                    ImageCms.createProfile("sRGB"),
                    outputMode="RGB",
                )
                if alpha is not None:
                    image.putalpha(alpha)
            except (ImageCms.PyCMSError, OSError):
                image = image.convert("RGBA" if alpha else "RGB")
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA" if "transparency" in image.info else "RGB")
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, format="WEBP", quality=84, method=6)


def import_images(product_id: int, main: Path, gallery: list[Path]) -> list[str]:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    product = next((item for item in catalog["products"] if item["id"] == product_id), None)
    if not product:
        raise ValueError(f"Não existe produto com ID {product_id} no catálogo.")

    sources = [main, *gallery]
    resolved_sources = [source.expanduser().resolve() for source in sources]
    missing = [source for source in resolved_sources if not source.is_file()]
    if missing:
        raise FileNotFoundError("Imagem não encontrada: " + ", ".join(str(path) for path in missing))

    paths = []
    for index, source in enumerate(resolved_sources):
        suffix = "main" if index == 0 else f"detail-{index}"
        filename = f"product-{product_id:02d}-{suffix}.webp"
        optimize_image(source, OUTPUT_DIR / filename)
        paths.append(f"assets/images/products/{filename}")

    product["image"] = paths[0]
    product["gallery"] = paths
    temporary_path = CATALOG_PATH.with_suffix(".json.tmp")
    temporary_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary_path, CATALOG_PATH)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product-id", required=True, type=int, help="ID do produto no catálogo")
    parser.add_argument("--main", required=True, type=Path, help="Foto principal do produto")
    parser.add_argument("--gallery", nargs="*", type=Path, default=[], help="Fotos adicionais, na ordem desejada")
    args = parser.parse_args()

    if len(args.gallery) > 5:
        parser.error("Informe no máximo cinco imagens adicionais.")
    try:
        paths = import_images(args.product_id, args.main, args.gallery)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    print(f"Imagens do produto {args.product_id} importadas:")
    for path in paths:
        print(f"  {path}")
    print("Reinicie o servidor para sincronizar o catálogo com o banco de dados.")


if __name__ == "__main__":
    main()
