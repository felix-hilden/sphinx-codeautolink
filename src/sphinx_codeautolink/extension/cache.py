"""Extension data cache."""
import json

from dataclasses import asdict
from typing import Dict, List
from pathlib import Path

from .block import SourceTransform, CodeExample, Name


class DataCache:
    """Data cache."""

    cache_filename = 'codeautolink-cache.json'

    def __init__(self, srcdir: str):
        self.srcdir: Path = Path(srcdir)
        self.transforms: Dict[str, List[SourceTransform]] = {}

    def read(self):
        """Read from cache."""
        cache = self.srcdir / self.cache_filename
        if not cache.exists():
            return
        content = json.loads(cache.read_text('utf-8'))
        for file, transforms in content.items():
            full_path = self.srcdir / (file + '.rst')
            if not full_path.exists():
                continue
            for transform in transforms:
                transform['example'] = CodeExample(**transform['example'])
                transform['names'] = [Name(**n) for n in transform['names']]
            self.transforms[file] = [SourceTransform(**t) for t in transforms]

    def write(self):
        """Write to cache."""
        cache = self.srcdir / self.cache_filename
        transforms_dict = {}
        for file, transforms in self.transforms.items():
            transforms_dict[file] = [asdict(t) for t in transforms]
        cache.write_text(json.dumps(transforms_dict, indent=2), 'utf-8')
