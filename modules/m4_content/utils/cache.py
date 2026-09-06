import hashlib
import json
from pathlib import Path


def file_hash(path):

    if not Path(path).exists():
        return None

    h = hashlib.sha256()

    with open(
        path,
        "rb"
    ) as f:

        while chunk := f.read(8192):
            h.update(chunk)

    return h.hexdigest()



def save_hash(
    path,
    hash_value
):

    with open(
        path,
        "w"
    ) as f:

        json.dump(
            {
                "hash": hash_value
            },
            f
        )



def load_hash(path):

    if not Path(path).exists():
        return None

    with open(path) as f:
        return json.load(f)["hash"]