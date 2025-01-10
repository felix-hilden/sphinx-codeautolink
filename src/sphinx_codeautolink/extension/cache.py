"""Extension data cache."""

import json
from dataclasses import asdict
from pathlib import Path

from .block import CodeExample, Name, SourceTransform


class DataCache:
    """Data cache."""

    cache_filename = "codeautolink-cache.json"

    def __init__(self, cache_dir: str, src_dir: str) -> None:
        self.cache_dir: Path = Path(cache_dir)
        self.src_dir: Path = Path(src_dir)
        self.transforms: dict[str, list[SourceTransform]] = {}

    def read(self) -> None:
        """Read from cache."""
        cache = self.cache_dir / self.cache_filename
        if not cache.exists():
            return
        content = json.loads(cache.read_text("utf-8"))
        for file, transforms in content.items():
            full_path = self.src_dir / (file + ".rst")
            if not full_path.exists():
                continue
            for transform in transforms:
                transform["example"] = CodeExample(**transform["example"])
                transform["names"] = [Name(**n) for n in transform["names"]]
            self.transforms[file] = [SourceTransform(**t) for t in transforms]

    def write(self) -> None:
        """Write to cache."""
        cache = self.cache_dir / self.cache_filename
        transforms_dict = {}
        for file, transforms in self.transforms.items():
            transforms_dict[file] = [asdict(t) for t in transforms]
        cache.write_text(json.dumps(transforms_dict, indent=2), "utf-8")
