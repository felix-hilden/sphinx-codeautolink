"""Analyse AST of code blocks to determine used names and their sources."""
import ast
import sys

from contextlib import contextmanager
from enum import Enum
from functools import wraps
from importlib import import_module
from typing import Dict, Union, List, Optional, Tuple
from warnings import warn
from dataclasses import dataclass, field


def parse_names(source: str) -> List['Name']:
    """Parse names from source."""
    tree = ast.parse(source)
    visitor = ImportTrackerVisitor()
    visitor.visit(tree)
    return sum([split_access(a) for a in visitor.accessed], [])


@dataclass
class PendingAccess:
    """Pending name access."""

    components: List[ast.AST]


@dataclass
class Component:
    """Name access component."""

    name: str
    lineno: int
    end_lineno: int
    context: str  # as in ast.Load / Store / Del

    @classmethod
    def from_ast(cls, node):
        """Generate a Component from an AST node."""
        context = 'load'
        if isinstance(node, ast.Name):
            name = node.id
            context = node.ctx.__class__.__name__.lower()
        elif isinstance(node, ast.Attribute):
            name = node.attr
            context = node.ctx.__class__.__name__.lower()
        elif isinstance(node, ast.Call):
            name = NameBreak.call
        else:
            raise ValueError(f'Invalid AST for component: {node.__class__.__name__}')
        end_lineno = getattr(node, 'end_lineno', node.lineno)
        return cls(name, node.lineno, end_lineno, context)


class NameBreak(str, Enum):
    """Elements that break name access chains."""

    call = '()'


class LinkContext(str, Enum):
    """Context in which a link appears."""

    none = 'none'
    after_call = 'after_call'
    import_from = 'import_from'  # from *mod.sub* import foo
    import_target = 'import_target'  # from mod.sub import *foo*


@dataclass
class Name:
    """A name accessed in the source traced back to an import."""

    import_components: List[str]
    code_str: str
    lineno: int
    end_lineno: int
    context: LinkContext = None
    resolved_location: str = None


@dataclass
class Access:
    """
    Accessed import, to be broken down into suitable chunks.

    :attr:`prior_components` are components that are implicitly used via
    the base name in :attr:`components`, which is the part that shows on the line.
    :attr:`hidden_components` is an attribute of split Access, in which the
    proper components are not moved to prior components to track which were
    present on the line of the access.

    The base component that connects an import to the name that was used to
    access it is automatically removed from the components in :attr:`full_components`.
    """

    context: LinkContext
    prior_components: List[Component]
    components: List[Component]
    hidden_components: List[Component] = field(default_factory=list)

    @property
    def full_components(self):
        """All components from import base to used components."""
        if not self.prior_components:
            # Import statement itself
            return self.hidden_components + self.components

        if self.hidden_components:
            proper_components = self.hidden_components[1:] + self.components
        else:
            proper_components = self.components[1:]
        return self.prior_components + proper_components

    @property
    def code_str(self):
        """Code representation of components."""
        breaks = set(NameBreak)
        return '.'.join(c.name for c in self.components if c.name not in breaks)

    @property
    def lineno_span(self) -> Tuple[int, int]:
        """Estimate the lineno span of components."""
        min_ = min(c.lineno for c in self.components)
        max_ = max(c.end_lineno for c in self.components)
        return min_, max_


def split_access(access: Access) -> List[Name]:
    """Split access into multiple names."""
    split = [access]
    while True:
        current = split[-1]
        for i, comp in enumerate(current.components):
            if i and comp.name == NameBreak.call:
                hidden = current.hidden_components + current.components[:i]
                next_ = Access(
                    LinkContext.after_call,
                    current.prior_components,
                    current.components[i:],
                    hidden_components=hidden,
                )
                current.components = current.components[:i]
                split.append(next_)
                break
        else:
            break
    if split[-1].components[-1].name == NameBreak.call:
        split.pop()
    return [
        Name(
            [c.name for c in s.full_components],
            s.code_str,
            *s.lineno_span,
            context=s.context,
        )
        for s in split
    ]


@dataclass
class Assignment:
    """Assignment of value to name."""

    to: Optional[PendingAccess]
    value: Optional[PendingAccess]


def track_parents(func):
    """
    Track a stack of nodes to determine the position of the current node.

    Uses and increments the surrounding classes :attr:`_parents`.
    """
    @wraps(func)
    def wrapper(self: 'ImportTrackerVisitor', *args, **kwargs):
        self._parents += 1
        r: Union[PendingAccess, Assignment, None] = func(self, *args, **kwargs)
        self._parents -= 1
        if not self._parents:
            if isinstance(r, Assignment):
                self._resolve_assignment(r)
            elif isinstance(r, PendingAccess):
                self._access(r)
        return r
    return wrapper


class ImportTrackerVisitor(ast.NodeVisitor):
    """Track imports and their use through source code."""

    def __init__(self):
        super().__init__()
        self.accessed: List[Access] = []
        self.in_augassign = False
        self._parents = 0

        # Stack for dealing with class body pseudo scopes
        # which are completely bypassed by inner scopes (func, lambda).
        # Current values are copied to the next class body level.
        self.pseudo_scopes_stack: List[Dict[str, List[Component]]] = [{}]
        # Stack for dealing with nested scopes.
        # Holds references to the values of previous nesting levels.
        self.outer_scopes_stack: List[Dict[str, List[Component]]] = []

    @contextmanager
    def reset_parents(self):
        """Reset parents state for the duration of the context."""
        self._parents, old = (0, self._parents)
        yield
        self._parents = old

    track_nodes = (
        ast.Name,
        ast.Attribute,
        ast.Call,
        ast.Assign,
        ast.AnnAssign,
    )
    if sys.version_info >= (3, 8):
        track_nodes += (ast.NamedExpr,)

    def visit(self, node: ast.AST):
        """Override default visit to track name access and assignments."""
        if not isinstance(node, self.track_nodes):
            with self.reset_parents():
                return super().visit(node)

        return super().visit(node)

    def _overwrite(self, name: str):
        """Overwrite name in current scope."""
        # Technically dotted values could now be bricked,
        # but we can't prevent the earlier values in the chain from being used.
        # There is a chance that the value which was assigned is a something
        # that we could follow, but for now it's not really worth the effort.
        # With a dotted value, the following condition will never hold as long
        # as the dotted components of imports are discarded on creating the import.
        self.pseudo_scopes_stack[-1].pop(name, None)

    def _assign(self, local_name: str, components: List[Component]):
        """Import or assign a name."""
        self._overwrite(local_name)  # Technically unnecessary unless we follow dots
        self.pseudo_scopes_stack[-1][local_name] = components

    def _access(self, access: PendingAccess) -> Optional[Access]:
        components = [Component.from_ast(n) for n in access.components]
        prior = self.pseudo_scopes_stack[-1].get(components[0].name, None)

        if prior is None:
            return

        context = components[0].context
        if context == 'store' and not self.in_augassign:
            self._overwrite(components[0].name)
            return

        access = Access(LinkContext.none, prior, components)
        self.accessed.append(access)
        if context == 'del':
            self._overwrite(components[0].name)
        return access

    def _resolve_assignment(self, assignment: Assignment):
        value = assignment.value
        access = self._access(value) if value is not None else None

        if assignment.to is None:
            return

        if len(assignment.to.components) == 1:
            comp = Component.from_ast(assignment.to.components[0])
            self._overwrite(comp.name)
            if access is not None:
                self._assign(comp.name, access.full_components)
        else:
            self._access(assignment.to)

    def _access_simple(self, name: str, lineno: int) -> Optional[Access]:
        component = Component(name, lineno, lineno, 'load')
        prior = self.pseudo_scopes_stack[-1].get(component.name, None)

        if prior is None:
            return

        access = Access(LinkContext.none, prior, [component])
        self.accessed.append(access)
        return access

    def visit_Global(self, node: ast.Global):
        """Import from top scope."""
        if not self.outer_scopes_stack:
            return  # in outermost scope already, no-op for imports

        imports = self.outer_scopes_stack[0]
        for name in node.names:
            self._overwrite(name)
            if name in imports:
                self._assign(name, imports[name])
                self._access_simple(name, node.lineno)

    def visit_Nonlocal(self, node: ast.Nonlocal):
        """Import from intermediate scopes."""
        imports_stack = self.outer_scopes_stack[1:]
        for name in node.names:
            self._overwrite(name)
            for imports in imports_stack[::-1]:
                if name in imports:
                    self.pseudo_scopes_stack[-1][name] = imports[name]
                    self._access_simple(name, node.lineno)
                    break

    def visit_Import(self, node: Union[ast.Import, ast.ImportFrom], prefix: str = ''):
        """Register import source."""
        import_star = (node.names[0].name == '*')
        if import_star:
            try:
                mod = import_module(node.module)
            except ImportError:
                warn(f'Could not import module `{node.module}` for parsing!')
                return
            import_names = [name for name in mod.__dict__ if not name.startswith('_')]
            aliases = [None] * len(import_names)
        else:
            import_names = [name.name for name in node.names]
            aliases = [name.asname for name in node.names]

        end_lineno = getattr(node, 'end_lineno', node.lineno)
        prefix_parts = prefix.rstrip('.').split('.') if prefix else []
        prefix_components = [
            Component(n, node.lineno, end_lineno, 'load') for n in prefix_parts
        ]
        if prefix:
            self.accessed.append(Access(LinkContext.import_from, [], prefix_components))

        for import_name, alias in zip(import_names, aliases):
            if not import_star:
                components = [
                    Component(n, node.lineno, end_lineno, 'load')
                    for n in import_name.split('.')
                ]
                self.accessed.append(
                    Access(LinkContext.import_target, [], components, prefix_components)
                )

            if not alias and '.' in import_name:
                # equivalent to only import top level module since we don't
                # follow assignments and the outer modules also get imported
                import_name = import_name.split('.')[0]

            full_components = [
                Component(n, node.lineno, end_lineno, 'store')
                for n in (prefix + import_name).split('.')
            ]
            self._assign(alias or import_name, full_components)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Register import source."""
        if node.level:  # relative import
            for name in node.names:
                self._overwrite(name.asname or name.name)
        else:
            self.visit_Import(node, prefix=node.module + '.')

    @track_parents
    def visit_Name(self, node):
        """Visit a Name node."""
        return PendingAccess([node])

    @track_parents
    def visit_Attribute(self, node):
        """Visit an Attribute node."""
        inner: PendingAccess = self.visit(node.value)
        if inner is not None:
            inner.components.append(node)
        return inner

    @track_parents
    def visit_Call(self, node: ast.Call):
        """Visit a Call node."""
        inner: PendingAccess = self.visit(node.func)
        if inner is not None:
            inner.components.append(node)
        with self.reset_parents():
            for arg in node.args + node.keywords:
                self.visit(arg)
            if hasattr(node, 'starargs'):
                self.visit(node.starargs)
            if hasattr(node, 'kwargs'):
                self.visit(node.kwargs)
        return inner

    @track_parents
    def visit_Assign(self, node: ast.Assign):
        """Visit an Assign node."""
        value = self.visit(node.value)
        target_returns = []
        for n in node.targets:
            target_returns.append(self.visit(n))
        if len(target_returns) == 1:
            return Assignment(target_returns[0], value)
        else:
            return value

    @track_parents
    def visit_AnnAssign(self, node: ast.AnnAssign):
        """Visit an AnnAssign node."""
        if node.value is not None:
            value = self.visit(node.value)
        target = self.visit(node.target)

        with self.reset_parents():
            self.visit(node.annotation)

        if node.value is not None:
            return Assignment(target, value)

    def visit_AugAssign(self, node: ast.AugAssign):
        """Visit an AugAssign node."""
        self.visit(node.value)
        self.in_augassign, temp = (True, self.in_augassign)
        self.visit(node.target)
        self.in_augassign = temp

    @track_parents
    def visit_NamedExpr(self, node):
        """Visit a NamedExpr node."""
        value = self.visit(node.value)
        target = self.visit(node.target)
        return Assignment(target, value)

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

        self._overwrite(node.name)
        self.pseudo_scopes_stack.append(self.pseudo_scopes_stack[0].copy())
        for b in node.body:
            self.visit(b)
        self.pseudo_scopes_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Delegate to func def."""
        self.visit_FunctionDef(node)

    @staticmethod
    def _get_args(node: ast.arguments):
        posonly = getattr(node, 'posonlyargs', [])  # only on 3.8+
        return node.args + node.kwonlyargs + posonly

    def visit_FunctionDef(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]):
        """Swap node order and separate inner scope."""
        self._overwrite(node.name)
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
        inner.pseudo_scopes_stack[0] = self.pseudo_scopes_stack[0].copy()
        inner.outer_scopes_stack = list(self.outer_scopes_stack)
        inner.outer_scopes_stack.append(self.pseudo_scopes_stack[0])
        for arg in args:
            if arg is None:
                continue
            inner._overwrite(arg.arg)
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
        inner.pseudo_scopes_stack[0] = self.pseudo_scopes_stack[0].copy()
        for arg in args:
            if arg is None:
                continue
            inner._overwrite(arg.arg)
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
        inner.pseudo_scopes_stack[0] = self.pseudo_scopes_stack[-1].copy()
        for gen in generators:
            inner.visit(gen)
        for value in values:
            inner.visit(value)
        self.accessed.extend(inner.accessed)
