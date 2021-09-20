"""Analyse AST of code blocks to determine used names and their sources."""
import ast

from typing import Dict, Set, Union, List
from dataclasses import dataclass


@dataclass
class Name:
    """A name accessed in the source traced back to an import."""

    import_name: str
    used_name: str
    lineno: int
    end_lineno: int


def parse_names(source: str) -> List[Name]:
    """Parse names from source."""
    tree = ast.parse(source)
    visitor = ImportTrackerVisitor()
    visitor.visit(tree)
    return visitor.accessed


class ImportTrackerVisitor(ast.NodeVisitor):
    """Track imports and their use through source code."""

    def __init__(self):
        self.imports: Dict[str, str] = {}
        self.assigned: Set[str] = set()
        self.accessed: List[Name] = []
        self.in_augassign = False
        super().__init__()

    def _maybe_remove_name(self, name: str):
        if name in self.imports:
            del self.imports[name]
        if name in self.assigned:
            self.assigned.remove(name)

    def _assign(self, name: str):
        self._maybe_remove_name(name)
        for im in list(self.imports):
            # Technically dotted imports could now be bricked so we remove them,
            # but we can't prevent the earlier items in the chain from being used.
            # There is a chance that what was assigned is a something that
            # we could follow, but it's not worth it for now.
            if ('.' in name and im.startswith(name)) or im.startswith(name + '.'):
                del self.imports[im]
        self.assigned.add(name)

    def _import(self, local_name: str, import_name: str):
        self._maybe_remove_name(local_name)
        if '.' in local_name:  # import all modules on the way
            split = local_name.split('.')
            for i in range(len(split)):
                name = '.'.join(split[:i + 1])
                self.imports[name] = name  # cannot be aliased if dotted
        else:
            self.imports[local_name] = import_name

    def visit_Import(self, node: Union[ast.Import, ast.ImportFrom], prefix: str = ''):
        """Register import source."""
        for name in node.names:
            self._import(name.asname or name.name, prefix + name.name)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Register import source."""
        if node.level:  # relative import
            for name in node.names:
                self._assign(name.asname or name.name)
        else:
            self.visit_Import(node, prefix=node.module + '.')

    def visit_Name(self, node):
        """Assign name or mark as accessed."""
        if isinstance(node.ctx, ast.Store) and not self.in_augassign:
            self._assign(node.id)
        elif node.id in self.imports:
            end_lineno = getattr(node, 'end_lineno', node.lineno)
            name = Name(self.imports[node.id], node.id, node.lineno, end_lineno)
            self.accessed.append(name)

    def visit_Attribute(self, node):
        """Recursively assign name or mark as accessed."""
        attrs = []
        inner = node
        while isinstance(inner, ast.Attribute):
            attrs.append(inner.attr)
            inner = inner.value

        if not isinstance(inner, ast.Name):
            self.visit(inner)
            return

        attrs.append(inner.id)
        full = '.'.join(reversed(attrs))

        if isinstance(node.ctx, ast.Store) and not self.in_augassign:
            self._assign(full)
        else:
            for im in self.imports:
                if full.startswith(im):
                    import_name = self.imports[im] + full[len(im):]
                    end_lineno = getattr(node, 'end_lineno', node.lineno)
                    name = Name(import_name, full, node.lineno, end_lineno)
                    self.accessed.append(name)
                    break

    def visit_Assign(self, node: ast.Assign):
        """Swap node order."""
        self.visit(node.value)
        for n in node.targets:
            self.visit(n)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        """Swap node order."""
        self.visit(node.value)
        self.visit(node.target)
        self.visit(node.annotation)

    def visit_AugAssign(self, node: ast.AugAssign):
        """Swap node order and handle augmented assignment not producing a new name."""
        self.in_augassign, temp = (True, self.in_augassign)
        self.visit(node.value)
        self.visit(node.target)
        self.in_augassign = temp

    def visit_NamedExpr(self, node):
        """Swap node order."""
        self.visit(node.value)
        self.visit(node.target)

    def visit_For(self, node: ast.For):
        """Swap node order."""
        self.visit(node.iter)
        self.visit(node.target)
        for n in node.body:
            self.visit(n)
        for n in node.orelse:
            self.visit(n)
