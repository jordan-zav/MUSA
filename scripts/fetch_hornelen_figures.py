"""Inspect public author figure originals; never label samples by filename alone."""
import json
import re

import pymupdf

from fetch_extended_benchmarks import ROOT, download


def main():
    folder = ROOT / "hornelen_sahu_2021"
    records = []
    url = "https://adgeo.copernicus.org/articles/56/117/2021/adgeo-56-117-2021.pdf"
    article = download(url, folder / "original/article.pdf")
    with pymupdf.open(article["path"]) as pdf:
        for number, page in enumerate(pdf):
            text = page.get_text()
            if not re.search(r"Figure\s+[78]\.", text):
                continue
            record = dict(article=article, page=number+1)
            record.update(text=page.get_text(), drawings=len(page.get_drawings()), images=[])
            page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(folder / f"page_{number+1}_preview.png")
            for index, image in enumerate(page.get_images(full=True)):
                info = pdf.extract_image(image[0])
                path = folder / "original" / f"page_{number+1}_image_{index}.{info['ext']}"
                if not path.exists():
                    path.write_bytes(info["image"])
                record["images"].append(dict(path=str(path), width=info["width"], height=info["height"],
                                             page_rects=[list(r) for r in page.get_image_rects(image[0])]))
            records.append(record)
            print(json.dumps(record), flush=True)
    (folder / "provenance.json").write_text(json.dumps(dict(article="10.5194/adgeo-56-117-2021", license="CC BY 4.0 article figures; modified from Odling 1997", files=records), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
