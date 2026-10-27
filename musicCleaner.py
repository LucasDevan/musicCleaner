import argparse
import re
import sys
import unicodedata
from pathlib import Path

try:
    from mutagen import File as MutagenFile
    from mutagen.easyid3 import EasyID3
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    from mutagen.oggvorbis import OggVorbis
except ImportError:
    raise SystemExit(
        "Missing dependency: install mutagen with `pip install mutagen` before running this script."
    )

# Keyword-to-artist mapping.
ARTIST_KEYWORDS = {
    "Undertale Yellow": "Undertale Yellow",
    "DELTARUNE": "Tobyfox",
    "deltarune": "Tobyfox",
    "deltarun": "Tobyfox",
    "DELTARUN": "Tobyfox",
    "TERRARIA": "Terraria_OST",
    "UNDERTALE": "Tobyfox",
    "POKEMON": "Pokemon",
    "MARIO": "Mario",
    "ZELDA": "Zelda",
    "Dream SMP": "DreamSMP",
    "Dreamsmp": "DreamSMP",
    "Fez": "Fez",
    "OneShot": "OneShot",
    "One shot": "OneShot",
    "Hollow Knight": "HollowKnight",
    "Celeste": "Celeste",
    "Tunic": "Tunic",
    "Re-Zero": "ReZero",
    "Re:Zero": "ReZero",
    "ReZero": "ReZero",
    "FTL": "FTL",
    "Nintendo": "Nintendo",
    "SANABI": "Sanabi",
    "CG5": "CG5",
    "KPop Demon Hunters": "KPopDemonHunters",
    "Geass": "CodeGeass",
    "Core Keeper": "CoreKeeper",
    "Daft Punk": "DaftPunk",
    "C418": "C418",
    "Fullmetal Alchemist": "FullmetalAlchemist",
    "Overlord": "Overlord",
    "Attack on Titan": "AttackOnTitan",
    "AttackonTitan": "AttackOnTitan",
}

AUDIO_EXTENSIONS = {"mp3", "flac", "m4a", "mp4", "ogg", "wav", "opus", "aiff", "ape"}

CHARACTER_TO_REMOVE = {
    # Add any additional characters you want to remove here.
    '」',
    '『',
    "【",
    "】",
    " ║",
    "「",
    "]",
    "[",
    "\""

}

def is_cjk(char: str) -> bool:
    codepoint = ord(char)
    return (
        0x4E00 <= codepoint <= 0x9FFF
        or 0x3400 <= codepoint <= 0x4DBF
        or 0x20000 <= codepoint <= 0x2A6DF
        or 0x2A700 <= codepoint <= 0x2B73F
        or 0x2B740 <= codepoint <= 0x2B81F
        or 0x2B820 <= codepoint <= 0x2CEAF
        or 0xF900 <= codepoint <= 0xFAFF
        or 0x2F800 <= codepoint <= 0x2FA1F
        or 0x3040 <= codepoint <= 0x309F
        or 0x30A0 <= codepoint <= 0x30FF
        or 0xAC00 <= codepoint <= 0xD7AF
    )


def normalize_filename(name: str) -> str:
    #name = EMOJI_PATTERN.sub("", name)
    cleaned_chars = []

    for char in name:
        if is_cjk(char):
            cleaned_chars.append(char)
            continue

        cat = unicodedata.category(char)
        if cat.startswith("L") or cat.startswith("N") or cat == "Zs":
            cleaned_chars.append(char)
            continue

        if char in {" ", "-","_"}:
            cleaned_chars.append(char)
            continue

        # Keep common ascii characters if they are not punctuation/math symbols.
        if char.isascii() and char.isprintable() and not cat.startswith("P") and not cat.startswith("S"):
            cleaned_chars.append(char)
            continue

        # Drop punctuation, symbol, math, and other unwanted characters.

    cleaned = "".join(cleaned_chars)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    cleaned = cleaned.replace("_128k", "").replace("_256k", "").replace("_320k", "").replace("__", "_").replace("--", "-").replace("  ", " ")

    # Collapse consecutive dashes to a single dash
    cleaned = re.sub(r"-{2,}", "-", cleaned)

    return cleaned


def find_artist_from_name(name: str) -> str | None:
    for keyword, artist in ARTIST_KEYWORDS.items():
        if keyword.lower() in name.lower():
            return artist
    return None

def update_audio_metadata(path: Path, artist: str) -> bool:
    suffix = path.suffix.lower().lstrip(".")
    try:
        if suffix == "mp3":
            audio = EasyID3(path)
            audio["artist"] = [artist]
            audio.save()
            return True
        if suffix == "flac":
            audio = FLAC(path)
            audio["artist"] = [artist]
            audio.save()
            return True
        if suffix in {"m4a", "mp4"}:
            audio = MP4(path)
            audio.tags["\xa9ART"] = [artist]
            audio.save()
            return True
        if suffix == "ogg":
            audio = OggVorbis(path)
            audio["artist"] = [artist]
            audio.save()
            return True
        if suffix in {"wav", "opus", "aiff", "ape"}:
            audio = MutagenFile(path, easy=True)
            if audio is None:
                return False
            audio["artist"] = [artist]
            audio.save()
            return True
    except Exception as exc:
        print(f"Warning: could not update metadata for {path.name}: {exc}")
    return False


def process_file(path: Path, dry_run: bool = False) -> None:
    original_name = path.stem
    extension = path.suffix
    
    new_stem = normalize_filename(original_name)
    new_name = f"{new_stem}{extension}"

    if new_name != path.name:
        target_path = path.with_name(new_name)
        if target_path.exists():
            print(f"Skipping rename because target already exists: {target_path}")
        else:
            print(f"Rename: {path.name} -> {new_name}")
            if not dry_run:
                path.rename(target_path)
                path = target_path
    
    artist = find_artist_from_name(new_name)
    if artist and path.suffix.lower().lstrip(".") in AUDIO_EXTENSIONS:
        #print(f"Update metadata artist for {path.name}: {artist}")
        if not dry_run:
            update_audio_metadata(path, artist)


def process_directory(directory: Path, recursive: bool = False, dry_run: bool = False) -> None:
    if recursive:
        files = [p for p in directory.rglob("*") if p.is_file()]
    else:
        files = [p for p in directory.iterdir() if p.is_file()]

    # Build file info list for duplicate detection
    file_infos = []

    fileName : str
    for p in files:
        fileName = p.stem.replace(p.suffix,"")
        for m in ["1","2","3","4","5"]:
            fileName = fileName.replace(m,"")
        try:
            size = p.stat().st_size
        except Exception:
            size = 0
        file_infos.append({"path": p, "norm": fileName, "size": size})

    # Group by (normalized name, length) when length is available
    to_remove = set()

    for i in range(len(file_infos)):
        for j in range(i+1,len(file_infos)):
            if(file_infos[i]["norm"] == file_infos[j]["norm"]):
                if(file_infos[i]["size"] > file_infos[j]["size"]):
                    to_remove.add(file_infos[i]["path"])
                else:
                    to_remove.add(file_infos[j]["path"])

    for p in sorted(to_remove):
        if dry_run:
            print(f"Would delete heavier duplicate: {p}")
        else:
            try:
                print(f"Deleting heavier duplicate: {p}")
                p.unlink()
            except Exception as exc:
                print(f"Warning: could not delete {p}: {exc}")

    # Process remaining files (skip those removed)
    remaining = [fi["path"] for fi in file_infos if fi["path"] not in to_remove]
    for path in sorted(remaining):
        process_file(path, dry_run=dry_run)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rename music files to remove emojis/punctuation/math symbols and optionally update audio artist metadata."
    )
    parser.add_argument("directory", type=Path, help="Directory containing music files")
    parser.add_argument("--recursive", "-r", action="store_true", help="Process subdirectories recursively")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without renaming or writing metadata")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    directory = args.directory
    if not directory.exists() or not directory.is_dir():
        print(f"Error: directory does not exist: {directory}")
        return 1

    process_directory(directory, recursive=args.recursive, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
