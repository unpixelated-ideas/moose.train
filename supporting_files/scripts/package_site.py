"""Stage public files only; exclude raw feeds, backups, and extraction code."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]


def main():
    output = ROOT / "_site"
    output.mkdir(exist_ok=False)
    for pattern in ("*.html", "*.ico", "*.png", "CNAME", ".nojekyll", "moose_train_schedule.csv"):
        for source in ROOT.glob(pattern):
            shutil.copy2(source, output / source.name)
    for relative in ("supporting_files/assets", "supporting_files/extraction/source_csvs"):
        shutil.copytree(ROOT / relative, output / relative)


if __name__ == "__main__":
    main()
