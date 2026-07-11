import imagehash
from PIL import Image

from flagquiz.flags import Flag


def compute_hashes(flags: list[Flag]) -> dict[str, imagehash.ImageHash]:
    hashes = {}
    for flag in flags:
        with Image.open(flag.image_path) as img:
            hashes[flag.code] = imagehash.phash(img)
    return hashes


def distance(hash_a: imagehash.ImageHash, hash_b: imagehash.ImageHash) -> int:
    return hash_a - hash_b


def ranked_by_similarity(code: str, hashes: dict[str, imagehash.ImageHash]) -> list[str]:
    target_hash = hashes[code]
    other_codes = [c for c in hashes if c != code]
    return sorted(other_codes, key=lambda c: distance(target_hash, hashes[c]))
