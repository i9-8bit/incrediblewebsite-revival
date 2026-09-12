from __future__ import annotations

import json
import re
import shutil
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

INCOMING = ROOT / "incoming"
GAMES_DIR = ROOT / "games"
GAMES_JSON = ROOT / "games.json"


BROWSER_EXTENSIONS = {
    ".html",
    ".htm",
    ".zip",
}


EMULATOR_EXTENSIONS = {
    ".gb": ("Game Boy", "gb"),
    ".gbc": ("Game Boy Color", "gbc"),
    ".gba": ("Game Boy Advance", "gba"),
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-") or "game"


def pretty_title(filename: str) -> str:
    name = Path(filename).stem
    name = re.sub(r"[_-]+", " ", name)
    return name.strip().title() or "Untitled Game"


def load_games() -> list[dict]:
    if not GAMES_JSON.exists():
        return []

    try:
        data = json.loads(
            GAMES_JSON.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(data, list):
            raise ValueError(
                "games.json must contain a JSON array."
            )

        return data

    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"ERROR: games.json is not valid JSON: {exc}"
        )


def save_games(games: list[dict]) -> None:
    GAMES_JSON.write_text(
        json.dumps(
            games,
            indent=4,
            ensure_ascii=False
        ) + "\n",
        encoding="utf-8"
    )


def unique_title(
    games: list[dict],
    title: str
) -> str:

    existing = {
        str(game.get("title", "")).strip().lower()
        for game in games
    }

    if title.lower() not in existing:
        return title

    number = 2

    while (
        f"{title} {number}".lower()
        in existing
    ):
        number += 1

    return f"{title} {number}"


def extract_zip(
    source: Path,
    destination: Path
) -> None:

    destination.mkdir(
        parents=True,
        exist_ok=True
    )

    with zipfile.ZipFile(
        source,
        "r"
    ) as archive:

        for member in archive.infolist():

            member_path = Path(
                member.filename
            )

            if member.filename.startswith("/"):
                raise ValueError(
                    "Unsafe ZIP: absolute path detected."
                )

            if ".." in member_path.parts:
                raise ValueError(
                    "Unsafe ZIP: parent-directory traversal detected."
                )

            target = destination / member_path

            target.resolve().relative_to(
                destination.resolve()
            )

        archive.extractall(
            destination
        )


def find_html_root(
    folder: Path
) -> Path | None:

    direct_index = folder / "index.html"

    if direct_index.exists():
        return folder

    candidates = list(
        folder.rglob("index.html")
    )

    if len(candidates) == 1:
        return candidates[0].parent

    return None


def import_browser_file(
    source: Path,
    games: list[dict]
) -> dict:

    title = unique_title(
        games,
        pretty_title(source.name)
    )

    slug = slugify(title)

    destination = (
        GAMES_DIR
        / "browser"
        / slug
    )

    if destination.exists():
        raise FileExistsError(
            f"Destination already exists: {destination}"
        )

    destination.mkdir(
        parents=True,
        exist_ok=True
    )

    extension = source.suffix.lower()

    if extension in {
        ".html",
        ".htm"
    }:

        shutil.copy2(
            source,
            destination / "index.html"
        )

    elif extension == ".zip":

        extract_zip(
            source,
            destination
        )

        html_root = find_html_root(
            destination
        )

        if html_root is None:

            raise ValueError(
                "ZIP imported, but no unique index.html "
                "could be found."
            )

        if html_root != destination:

            temp = (
                destination.parent
                / f".{slug}-normalized"
            )

            if temp.exists():
                shutil.rmtree(temp)

            shutil.copytree(
                html_root,
                temp
            )

            shutil.rmtree(
                destination
            )

            temp.rename(
                destination
            )

    else:

        raise ValueError(
            f"Unsupported browser file: {extension}"
        )

    return {
        "title": title,
        "description": "User-added browser game.",
        "category": "Other",
        "platform": "Web",
        "type": "html",
        "url": (
            f"games/browser/{slug}/index.html"
        ),
        "featured": False,
        "tags": [
            "Browser"
        ]
    }


def import_emulator_file(
    source: Path,
    games: list[dict]
) -> dict:

    extension = source.suffix.lower()

    if extension not in EMULATOR_EXTENSIONS:
        raise ValueError(
            f"Unsupported emulator file: {extension}"
        )

    platform, core = (
        EMULATOR_EXTENSIONS[extension]
    )

    title = unique_title(
        games,
        pretty_title(source.name)
    )

    destination = (
        GAMES_DIR
        / "gameboys"
        / source.name
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if destination.exists():
        raise FileExistsError(
            f"Destination already exists: {destination}"
        )

    shutil.copy2(
        source,
        destination
    )

    return {
        "title": title,
        "description": f"{platform} game.",
        "category": "Gameboys",
        "platform": platform,
        "type": "emulator",
        "file": str(
            destination.relative_to(ROOT)
        ).replace("\\", "/"),
        "core": core,
        "featured": False,
        "tags": [
            "Retro",
            platform
        ]
    }


def import_file(
    source: Path,
    games: list[dict]
) -> dict:

    extension = source.suffix.lower()

    if extension in BROWSER_EXTENSIONS:
        return import_browser_file(
            source,
            games
        )

    if extension in EMULATOR_EXTENSIONS:
        return import_emulator_file(
            source,
            games
        )

    supported = sorted(
        BROWSER_EXTENSIONS
        | set(EMULATOR_EXTENSIONS)
    )

    raise ValueError(
        f"Unsupported file type: {extension}\n"
        f"Supported: {', '.join(supported)}"
    )


def main() -> None:

    if len(sys.argv) > 1:

        source = Path(
            sys.argv[1]
        )

        if not source.is_absolute():
            source = ROOT / source

    else:

        INCOMING.mkdir(
            parents=True,
            exist_ok=True
        )

        files = [
            path
            for path in INCOMING.iterdir()
            if path.is_file()
            and not path.name.startswith(".")
        ]

        if not files:

            print(
                "No games found in incoming/."
            )

            print(
                "Put a .html, .zip, .gb, .gbc, "
                "or .gba file in incoming/"
            )

            return

        if len(files) > 1:

            print(
                "Multiple files found in incoming/:"
            )

            for path in files:
                print(
                    f"  - {path.name}"
                )

            print(
                "\nImport one explicitly with:"
            )

            print(
                "python3 tools/import-game.py "
                "incoming/YOURFILE"
            )

            return

        source = files[0]

    if not source.exists():
        raise SystemExit(
            f"ERROR: File not found: {source}"
        )

    if not source.is_file():
        raise SystemExit(
            f"ERROR: Not a file: {source}"
        )

    games = load_games()

    print(
        f"Importing: {source.name}"
    )

    try:

        entry = import_file(
            source,
            games
        )

    except Exception as exc:

        raise SystemExit(
            f"ERROR: {exc}"
        )

    games.append(entry)

    save_games(games)

    print()
    print("SUCCESS!")
    print(
        f"Added: {entry['title']}"
    )

    if "url" in entry:
        print(
            f"URL:  {entry['url']}"
        )

    if "file" in entry:
        print(
            f"File: {entry['file']}"
        )

    print()
    print(
        "The game files and games.json "
        "have been updated."
    )

    print(
        "Now run:"
    )

    print(
        "git add ."
    )

    print(
        'git commit -m "Add game"'
    )

    print(
        "git push"
    )


if __name__ == "__main__":
    main()
