import json
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FLAGS_JSON_PATH = BASE_DIR / "data" / "flags.json"
FLAGS_IMAGE_DIR = BASE_DIR / "static" / "flags"


@dataclass(frozen=True)
class Flag:
    code: str
    name_ja: str
    name_en: str

    @property
    def image_path(self) -> Path:
        return FLAGS_IMAGE_DIR / f"{self.code}.png"


def load_flags(json_path: Path = FLAGS_JSON_PATH) -> list[Flag]:
    with open(json_path, encoding="utf-8") as f:
        raw = json.load(f)
    return [Flag(code=item["code"], name_ja=item["name_ja"], name_en=item["name_en"]) for item in raw]


def get_flag(code: str, flags: list[Flag]) -> Flag:
    for flag in flags:
        if flag.code == code:
            return flag
    raise KeyError(f"unknown flag code: {code}")


def find_flag(code: str | None, flags: list[Flag]) -> Flag | None:
    return next((flag for flag in flags if flag.code == code), None)
