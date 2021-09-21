"""Analyse AST of code blocks to determine used names and their sources."""
import ast

from typing import Dict, Union, List
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
        super().__init__()
        self.accessed: List[Name] = []
        self.in_augassign = False

        # Stack for dealing with class body pseudo scopes
        # which are completely bypassed by inner scopes (func, lambda).
        # Current imports are copied to the next class body level.
        self.imports_stack: List[Dict[str, str]] = [{}]
        # Stack for dealing with global and nonlocal statements.
        # Holds references to the imports of previous nesting levels.
        self.outer_scope_imports_stack: List[Dict[str, str]] = []

    def _remove_from_imports(self, name: str):
        """Overwrite name, deleting possible imports share the name."""
        # Technically dotted imports could now be bricked so we remove them,
        # but we can't prevent the earlier items in the chain from being used.
        # There is a chance that what was assigned is a something that
        # we could follow, but it's not worth it for now.
        for im in list(self.imports_stack[-1]):
            if im.startswith(name) or im.startswith(name + '.'):
                del self.imports_stack[-1][im]

    def _import(self, local_name: str, import_name: str):
        self._remove_from_imports(local_name)
        if '.' in local_name:  # import all modules on the way
            split = local_name.split('.')
            for i in range(len(split)):
                name = '.'.join(split[:i + 1])
                self.imports_stack[-1][name] = name  # cannot be aliased if dotted
        else:
            self.imports_stack[-1][local_name] = import_name

    def _use_import(self, import_name: str, used_name: str, node: ast.AST):
        end_lineno = getattr(node, 'end_lineno', node.lineno)
        name = Name(import_name, used_name, node.lineno, end_lineno)
        self.accessed.append(name)

    def visit_Global(self, node: ast.Global):
        """Import from top scope."""
        if not self.outer_scope_imports_stack:
            return  # in outermost scope already, no-op for imports

        imports = self.outer_scope_imports_stack[0]
        for name in node.names:
            self._remove_from_imports(name)
            if name in imports:
                self.imports_stack[-1][name] = imports[name]
                self._use_import(name, name, node)

    def visit_Nonlocal(self, node: ast.Nonlocal):
        """Import from intermediate scopes."""
        imports_stack = self.outer_scope_imports_stack[1:]
        for name in node.names:
            self._remove_from_imports(name)
            for imports in imports_stack[::-1]:
                if name in imports:
                    self.imports_stack[-1][name] = imports[name]
                    self._use_import(name, name, node)
                    break

    def visit_Import(self, node: Union[ast.Import, ast.ImportFrom], prefix: str = ''):
        """Register import source."""
        for name in node.names:
            self._import(name.asname or name.name, prefix + name.name)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Register import source."""
        if node.level:  # relative import
            for name in node.names:
                self._remove_from_imports(name.asname or name.name)
        else:
            self.visit_Import(node, prefix=node.module + '.')

    def visit_Name(self, node):
        """Assign name or mark as accessed."""
        if isinstance(node.ctx, ast.Store) and not self.in_augassign:
            self._remove_from_imports(node.id)
        elif node.id in self.imports_stack[-1]:
            import_ = self.imports_stack[-1][node.id]
            self._use_import(import_, node.id, node)
            if isinstance(node.ctx, ast.Del):
                self._remove_from_imports(node.id)

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
            self._remove_from_imports(full)
        else:
            for im in self.imports_stack[-1]:
                if full.startswith(im):
                    import_name = self.imports_stack[-1][im] + full[len(im):]
                    self._use_import(import_name, full, node)
                    if isinstance(node.ctx, ast.Del):
                        self._remove_from_imports(import_name)
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

    def visit_AsyncFor(self, node: ast.AsyncFor):
        """Delegate to sync for."""
        self.visit_AsyncFor(node)

    def visit_For(self, node: Union[ast.For, ast.AsyncFor]):
        """Swap node order."""
        self.visit(node.iter)
        self.visit(node.target)
        for n in node.body:
            self.visit(n)
        for n in node.orelse:
            self.visit(n)

    def visit_ClassDef(self, node: ast.ClassDef):
        """Handle pseudo scope of class body."""
        for dec in node.decorator_list:
            self.visit(dec)
        for base in node.bases:
            self.visit(base)
        for kw in node.keywords:
            self.visit(kw)

        self._remove_from_imports(node.name)
        self.imports_stack.append(self.imports_stack[0].copy())
        for b in node.body:
            self.visit(b)
        self.imports_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Delegate to func def."""
        self.visit_FunctionDef(node)

    @staticmethod
    def _get_args(node: ast.arguments):
        posonly = getattr(node, 'posonlyargs', [])  # only on 3.8+
        return node.args + node.kwonlyargs + posonly

    def visit_FunctionDef(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]):
        """Swap node order and separate inner scope."""
        self._remove_from_imports(node.name)
        for dec in node.decorator_list:
            self.visit(dec)
        if node.returns is not None:
            self.visit(node.returns)
        for d in node.args.defaults + node.args.kw_defaults:
            if d is None:
                continue
            self.visit(d)
        args = self._get_args(node.args)
        args += [node.args.vararg, node.args.kwarg]
        for arg in args:
            if arg is None or arg.annotation is None:
                continue
            self.visit(arg.annotation)

        inner = self.__class__()
        inner.imports_stack[0] = self.imports_stack[0].copy()
        inner.outer_scope_imports_stack = list(self.outer_scope_imports_stack)
        inner.outer_scope_imports_stack.append(self.imports_stack[0])
        for arg in args:
            if arg is None:
                continue
            inner._remove_from_imports(arg.arg)
        for n in node.body:
            inner.visit(n)
        self.accessed.extend(inner.accessed)

    def visit_Lambda(self, node: ast.Lambda):
        """Swap node order and separate inner scope."""
        for d in node.args.defaults + node.args.kw_defaults:
            if d is None:
                continue
            self.visit(d)
        args = self._get_args(node.args)
        args += [node.args.vararg, node.args.kwarg]

        inner = self.__class__()
        inner.imports_stack[0] = self.imports_stack[0].copy()
        for arg in args:
            if arg is None:
                continue
            inner._remove_from_imports(arg.arg)
        inner.visit(node.body)
        self.accessed.extend(inner.accessed)

    def visit_ListComp(self, node: ast.ListComp):
        """Delegate to generic comp."""
        self.visit_generic_comp([node.elt], node.generators)

    def visit_SetComp(self, node: ast.SetComp):
        """Delegate to generic comp."""
        self.visit_generic_comp([node.elt], node.generators)

    def visit_DictComp(self, node: ast.DictComp):
        """Delegate to generic comp."""
        self.visit_generic_comp([node.key, node.value], node.generators)

    def visit_GeneratorExp(self, node: ast.GeneratorExp):
        """Delegate to generic comp."""
        self.visit_generic_comp([node.elt], node.generators)

    def visit_comprehension(self, node: ast.comprehension):
        """Swap node order."""
        self.visit(node.iter)
        self.visit(node.target)
        for f in node.ifs:
            self.visit(f)

    def visit_generic_comp(
        self, values: List[ast.AST], generators: List[ast.comprehension]
    ):
        """Separate inner scope, respects class body scope."""
        inner = self.__class__()
        inner.imports_stack[0] = self.imports_stack[-1].copy()
        for gen in generators:
            inner.visit(gen)
        for value in values:
            inner.visit(value)
        self.accessed.extend(inner.accessed)
