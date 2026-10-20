"""Stage public files only; exclude raw feeds, backups, and extraction code."""
from pathlib import Path
import shutil
import gzip

ROOT = Path(__file__).resolve().parents[2]


def main(output=None):
    output = output or ROOT / "_site"
    output.mkdir(parents=True, exist_ok=False)
    for pattern in ("*.html", "*.ico", "*.png", "*.webmanifest", "CNAME", ".nojekyll", "moose_train_schedule.csv"):
        for source in ROOT.glob(pattern):
            shutil.copy2(source, output / source.name)
    compressed = ROOT / "moose_train_schedule.csv.gz"
    if compressed.exists():
        with gzip.open(compressed, "rb") as source, (output / "moose_train_schedule.csv").open("wb") as target:
            shutil.copyfileobj(source, target)
    for relative in ("supporting_files/assets", "supporting_files/extraction/source_csvs"):
        shutil.copytree(ROOT / relative, output / relative)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New output directory for a local publication check")
    main(parser.parse_args().output)
