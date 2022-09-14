"""Analyse AST of code blocks to determine used names and their sources."""
import ast
import sys
import builtins

from contextlib import contextmanager
from enum import Enum
from functools import wraps
from importlib import import_module
from typing import Dict, Union, List, Optional, Tuple
from dataclasses import dataclass, field

from .warn import logger, warn_type

HAS_WALRUS = (sys.version_info >= (3, 8))
HAS_MATCH = (sys.version_info >= (3, 10))


def parse_names(source: str, doctree_node) -> List['Name']:
    """Parse names from source."""
    tree = ast.parse(source)
    visitor = ImportTrackerVisitor(doctree_node)
    visitor.visit(tree)
    return visitor.accessed


def linenos(node: ast.AST) -> Tuple[int, int]:
    """Return lineno and end_lineno safely."""
    return node.lineno, getattr(node, 'end_lineno', node.lineno)


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
        elif isinstance(node, ast.arg):
            name = node.arg
        elif isinstance(node, ast.Call):
            name = NameBreak.call
        elif HAS_MATCH and isinstance(node, ast.MatchAs):
            name = node.name
            context = 'store'
        else:
            raise ValueError(f'Invalid AST for component: {node.__class__.__name__}')
        return cls(name, *linenos(node), context)


@dataclass
class PendingAccess:
    """Pending name access."""

    components: List[Component]


@dataclass
class AssignTarget:
    """
    Assign target.

    `elements` represent the flattened assignment target elements.
    If a single PendingAccess is found, it should be used to store the value
    on the right hand side of the assignment. If multiple values are found,
    the assignment contained unpacking, and only overwriting of names should occur.
    """

    elements: List[Optional[PendingAccess]]


@dataclass
class Assignment:
    """
    Representation of an assignment statement.

    - ordinarily one value to a single target
    - multiple targets when chain assigning (a = b = c)
    - nested assignments in walruses (a = b := c)
    """

    targets: List[AssignTarget]
    value: Union[PendingAccess, 'Assignment', None]


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
    context: Optional[LinkContext] = None
    resolved_location: Optional[str] = None


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
        break_on = set(NameBreak)
        breaks = [i for i, c in enumerate(self.components) if c.name in break_on]
        start_ix = breaks[-1] + 1 if breaks else 0
        return '.'.join(c.name for c in self.components[start_ix:])

    @property
    def lineno_span(self) -> Tuple[int, int]:
        """Estimate the lineno span of components."""
        min_ = min(c.lineno for c in self.components)
        max_ = max(c.end_lineno for c in self.components)
        return min_, max_

    @staticmethod
    def to_name(instance: 'Access') -> Name:
        """Convert access to name."""
        return Name(
            [c.name for c in instance.full_components],
            instance.code_str,
            *instance.lineno_span,
            context=instance.context,
        )

    def split(self) -> List[Name]:
        """Split access into multiple names."""
        # Copy to avoid modifying the instance in place
        items = [Access(
            context=self.context,
            prior_components=self.prior_components[:],
            components=self.components[:],
            hidden_components=self.hidden_components[:],
        )]
        while True:
            current = items[-1]
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
                    items.append(next_)
                    break
            else:
                break
        if items[-1].components[-1].name == NameBreak.call:
            items.pop()
        return [self.to_name(i) for i in items]


def track_parents(func):
    """
    Track a stack of nodes to determine the position of the current node.

    Uses and increments the surrounding classes :attr:`_parents`.
    """
    @wraps(func)
    def wrapper(self: 'ImportTrackerVisitor', *args, **kwargs):
        self._parents += 1
        result = func(self, *args, **kwargs)
        self._parents -= 1
        if not self._parents:
            self.dispatch_result(result)
        return result
    return wrapper


builtin_components: Dict[str, List[Component]] = {
    b: [Component(b, -1, -1, LinkContext.none)] for b in dir(builtins)
}


class ImportTrackerVisitor(ast.NodeVisitor):
    """Track imports and their use through source code."""

    def __init__(self, doctree_node):
        super().__init__()
        self.accessed: List[Name] = []
        self.in_augassign = False
        self._parents = 0
        self._no_split = False
        self.doctree_node = doctree_node

        # Stack for dealing with class body pseudo scopes
        # which are completely bypassed by inner scopes (func, lambda).
        # Current values are copied to the next class body level.
        self.pseudo_scopes_stack: List[Dict[str, List[Component]]] = [
            builtin_components.copy()
        ]
        # Stack for dealing with nested scopes.
        # Holds references to the values of previous nesting levels.
        self.outer_scopes_stack: List[Dict[str, List[Component]]] = []

    def save_access(self, access: Access) -> None:
        """Convert Access to Names to store in the visitor for aggregation."""
        names = access.split() if not self._no_split else [Access.to_name(access)]
        self.accessed.extend(names)

    @contextmanager
    def no_split(self):
        """Disable splitting Accesses."""
        self._no_split, old = (True, self._no_split)
        yield
        self._no_split = old

    @contextmanager
    def reset_parents(self):
        """Reset parents state for the duration of the context."""
        self._parents, old = (0, self._parents)
        yield
        self._parents = old

    # Nodes that are excempt from resetting parents in default visit
    track_nodes = (
        ast.Name,
        ast.Attribute,
        ast.Call,
    )
    if HAS_WALRUS:
        track_nodes += (ast.NamedExpr,)
    if HAS_MATCH:
        track_nodes += (ast.MatchAs,)

    def visit(self, node: ast.AST):
        """Override default visit to track name access and assignments."""
        if isinstance(node, self.track_nodes):
            return super().visit(node)

        with self.reset_parents():
            return super().visit(node)

    def overwrite_name(self, name: str):
        """Overwrite name in current scope."""
        # Technically dotted values could now be bricked,
        # but we can't prevent the earlier values in the chain from being used.
        # There is a chance that the value which was assigned is a something
        # that we could follow, but for now it's not really worth the effort.
        # With a dotted value, the following condition will never hold as long
        # as the dotted components of imports are discarded on creating the import.
        self.pseudo_scopes_stack[-1].pop(name, None)

    def assign_name(self, name: str, components: List[Component]):
        """Import or assign a name to current scope."""
        # Overwriting technically unnecessary until it properly follows dots
        self.overwrite_name(name)
        self.pseudo_scopes_stack[-1][name] = components

    def create_access(
        self, scope_key: str, new_components: List[Component]
    ) -> Optional[Access]:
        """Create access from scope."""
        prior = self.pseudo_scopes_stack[-1].get(scope_key, None)
        if prior is None:
            return

        access = Access(LinkContext.none, prior, new_components)
        self.save_access(access)
        return access

    def resolve_pending_access(self, pending: PendingAccess) -> Optional[Access]:
        """Resolve and save pending access."""
        components = pending.components

        context = components[0].context
        if context == 'store' and not self.in_augassign:
            self.overwrite_name(components[0].name)
            return

        access = self.create_access(components[0].name, components)
        if context == 'del':
            self.overwrite_name(components[0].name)
        return access

    def resolve_assignment(self, assignment: Assignment) -> Optional[Access]:
        """Resolve access for assignment values and targets."""
        access = self.dispatch_result(assignment.value)
        self._resolve_assign_targets(assignment, access)
        return access

    def _resolve_assign_targets(self, assignment: Assignment, access: Access):
        for assign in assignment.targets:
            if assign is None:
                continue

            # On multiple nested targets, only overwrite assigned names
            value = access if len(assign.elements) <= 1 else None

            for target in assign.elements:
                self._resolve_assign_target(target, value)

    def _resolve_assign_target(
        self, target: Optional[PendingAccess], value: Optional[Access]
    ):
        if target is None:
            return

        if len(target.components) == 1:
            comp = target.components[0]
            if value is None:
                self.overwrite_name(comp.name)
            else:
                self.assign_name(comp.name, value.full_components)
                self.create_access(comp.name, target.components)
        else:
            self.resolve_pending_access(target)

    def create_simple_access(self, name: str, lineno: int) -> None:
        """Create single-component access to scope."""
        component = Component(name, lineno, lineno, 'load')
        self.create_access(component.name, [component])

    def dispatch_result(
        self, result: Union[PendingAccess, Assignment, None]
    ) -> Optional[Access]:
        """Determine the appropriate processing after tracking an access chain."""
        if isinstance(result, Assignment):
            return self.resolve_assignment(result)
        elif isinstance(result, PendingAccess):
            return self.resolve_pending_access(result)

    def visit_Global(self, node: ast.Global):
        """Import from top scope."""
        if not self.outer_scopes_stack:
            return  # in outermost scope already, no-op for imports

        imports = self.outer_scopes_stack[0]
        for name in node.names:
            self.overwrite_name(name)
            if name in imports:
                self.assign_name(name, imports[name])
                self.create_simple_access(name, node.lineno)

    def visit_Nonlocal(self, node: ast.Nonlocal):
        """Import from intermediate scopes."""
        imports_stack = self.outer_scopes_stack[1:]
        for name in node.names:
            self.overwrite_name(name)
            for imports in imports_stack[::-1]:
                if name in imports:
                    self.assign_name(name, imports[name])
                    self.create_simple_access(name, node.lineno)
                    break

    def visit_Import(self, node: Union[ast.Import, ast.ImportFrom], prefix: str = ''):
        """Register import source."""
        import_star = (node.names[0].name == '*')
        if import_star:
            try:
                mod = import_module(node.module)
                import_names = [
                    name for name in mod.__dict__ if not name.startswith('_')
                ]
                aliases = [None] * len(import_names)
            except ImportError:
                logger.warning(
                    f'Could not import module `{node.module}` for parsing!',
                    type=warn_type,
                    subtype='import_star',
                    location=self.doctree_node,
                )
                import_names = []
                aliases = []
        else:
            import_names = [name.name for name in node.names]
            aliases = [name.asname for name in node.names]

        prefix_parts = prefix.rstrip('.').split('.') if prefix else []
        prefix_components = [
            Component(n, *linenos(node), 'load') for n in prefix_parts
        ]
        if prefix:
            self.save_access(Access(LinkContext.import_from, [], prefix_components))

        for import_name, alias in zip(import_names, aliases):
            if not import_star:
                components = [
                    Component(n, *linenos(node), 'load')
                    for n in import_name.split('.')
                ]
                self.save_access(
                    Access(LinkContext.import_target, [], components, prefix_components)
                )

            if not alias and '.' in import_name:
                # equivalent to only import top level module since we don't
                # follow assignments and the outer modules also get imported
                import_name = import_name.split('.')[0]

            full_components = [
                Component(n, *linenos(node), 'store')
                for n in (prefix + import_name).split('.')
            ]
            self.assign_name(alias or import_name, full_components)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Register import source."""
        if node.level:  # relative import
            for name in node.names:
                self.overwrite_name(name.asname or name.name)
        else:
            self.visit_Import(node, prefix=node.module + '.')

    @track_parents
    def visit_Name(self, node: ast.Name):
        """Visit a Name node."""
        return PendingAccess([Component.from_ast(node)])

    @track_parents
    def visit_Attribute(self, node: ast.Attribute):
        """Visit an Attribute node."""
        inner: Optional[PendingAccess] = self.visit(node.value)
        if inner is not None:
            inner.components.append(Component.from_ast(node))
        return inner

    @track_parents
    def visit_Call(self, node: ast.Call):
        """Visit a Call node."""
        inner: Optional[PendingAccess] = self.visit(node.func)
        if inner is not None:
            inner.components.append(Component.from_ast(node))
        with self.reset_parents():
            for arg in node.args + node.keywords:
                self.visit(arg)
            if hasattr(node, 'starargs'):
                self.visit(node.starargs)
            if hasattr(node, 'kwargs'):
                self.visit(node.kwargs)
        return inner

    @track_parents
    def visit_Tuple(self, node: ast.Tuple):
        """Visit a Tuple node."""
        if isinstance(node.ctx, ast.Store):
            accesses = []
            for element in node.elts:
                ret = self.visit(element)
                if isinstance(ret, PendingAccess) or ret is None:
                    accesses.append(ret)
                else:
                    accesses.extend(ret)
            return accesses
        else:
            with self.reset_parents():
                for element in node.elts:
                    self.visit(element)

    @track_parents
    def visit_Assign(self, node: ast.Assign):
        """Visit an Assign node."""
        value = self.visit(node.value)
        targets = []
        for n in node.targets[::-1]:
            target = self.visit(n)
            if not isinstance(target, list):
                target = [target]
            targets.append(AssignTarget(target))
        return Assignment(targets, value)

    @track_parents
    def visit_AnnAssign(self, node: ast.AnnAssign):
        """Visit an AnnAssign node."""
        value = self.visit(node.value) if node.value is not None else None
        annot = self.visit(node.annotation)
        if annot is not None:
            if value is not None:
                self.resolve_pending_access(value)

            annot.components.append(
                Component(NameBreak.call, *linenos(node.annotation), 'load')
            )
            value = annot

        target = self.visit(node.target)
        if value is not None:
            return Assignment([AssignTarget([target])], value)

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
        return Assignment([AssignTarget([target])], value)

    @track_parents
    def visit_MatchClass(self, node):
        """Visit a match case class as a series of assignments."""
        with self.reset_parents():
            cls = self.visit(node.cls)

        accesses = []
        for n in node.patterns:
            access = self.visit(n)
            if access is not None:
                accesses.append(access)

        assigns = []
        for attr, pattern in zip(node.kwd_attrs, node.kwd_patterns):
            target = self.visit(pattern)
            attr_comps = [
                Component(NameBreak.call, *linenos(node), 'load'),
                Component(attr, *linenos(node), 'load'),
            ]
            access = PendingAccess(cls.components + attr_comps)
            assigns.append(Assignment([AssignTarget([target])], access))

        for access in accesses:
            self.resolve_pending_access(access)

        with self.no_split():
            for assign in assigns:
                self.resolve_assignment(assign)

    @track_parents
    def visit_MatchAs(self, node):
        """Track match alias names."""
        return PendingAccess([Component.from_ast(node)])

    def visit_AsyncFor(self, node: ast.AsyncFor):
        """Delegate to sync for."""
        self.visit_For(node)

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

        self.overwrite_name(node.name)
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
        self.overwrite_name(node.name)
        for dec in node.decorator_list:
            self.visit(dec)
        for d in node.args.defaults + node.args.kw_defaults:
            if d is None:
                continue
            self.visit(d)
        args = self._get_args(node.args)
        args += [node.args.vararg, node.args.kwarg]

        inner = self.__class__(self.doctree_node)
        inner.pseudo_scopes_stack[0] = self.pseudo_scopes_stack[0].copy()
        inner.outer_scopes_stack = list(self.outer_scopes_stack)
        inner.outer_scopes_stack.append(self.pseudo_scopes_stack[0])

        for arg in args:
            if arg is None:
                continue
            inner.visit(arg)
        if node.returns is not None:
            self.visit(node.returns)
        for n in node.body:
            inner.visit(n)
        self.accessed.extend(inner.accessed)

    @track_parents
    def visit_arg(self, arg: ast.arg):
        """Handle function argument and its annotation."""
        target = PendingAccess([Component.from_ast(arg)])
        if arg.annotation is not None:
            value = self.visit(arg.annotation)
            if value is not None:
                value.components.append(
                    Component(NameBreak.call, *linenos(arg), 'load')
                )
        else:
            value = None
        return Assignment([AssignTarget([target])], value)

    def visit_Lambda(self, node: ast.Lambda):
        """Swap node order and separate inner scope."""
        for d in node.args.defaults + node.args.kw_defaults:
            if d is None:
                continue
            self.visit(d)
        args = self._get_args(node.args)
        args += [node.args.vararg, node.args.kwarg]

        inner = self.__class__(self.doctree_node)
        inner.pseudo_scopes_stack[0] = self.pseudo_scopes_stack[0].copy()
        for arg in args:
            if arg is None:
                continue
            inner.overwrite_name(arg.arg)
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
        inner = self.__class__(self.doctree_node)
        inner.pseudo_scopes_stack[0] = self.pseudo_scopes_stack[-1].copy()
        for gen in generators:
            inner.visit(gen)
        for value in values:
            inner.visit(value)
        self.accessed.extend(inner.accessed)
