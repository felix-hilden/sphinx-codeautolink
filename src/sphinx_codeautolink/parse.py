"""Analyse AST of code blocks to determine used names and their sources."""

from __future__ import annotations

import ast
import builtins
import sys
from dataclasses import dataclass
from enum import Enum
from importlib import import_module

from .warn import logger, warn_type

HAS_MATCH = sys.version_info >= (3, 10)


def parse_names(source: str, doctree_node) -> list[Name]:
    """Parse names from source."""
    tree = ast.parse(source)
    visitor = ImportTrackerVisitor(doctree_node)
    visitor.visit(tree)
    return visitor.accessed


def linenos(node: ast.AST) -> tuple[int, int]:
    """Return lineno and end_lineno safely."""
    return node.lineno, getattr(node, "end_lineno", node.lineno)


@dataclass
class Component:
    """Name access component."""

    name: str
    lineno: int
    end_lineno: int
    context: str  # as in ast.Load / Store / Del

    @classmethod
    def from_ast(cls, node: ast.AST) -> Component:
        """Generate a Component from an AST node."""
        context = "load"
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
        elif isinstance(node, ast.NamedExpr):
            name = NameBreak.namedexpr
        elif HAS_MATCH and isinstance(node, ast.MatchAs):
            name = node.name
            context = "store"
        else:
            msg = f"Invalid AST for component: {node.__class__.__name__}"
            raise ValueError(msg)
        return cls(name, *linenos(node), context)


@dataclass
class PendingAccess:
    """Name access chain pending to be resolved in the scope and recorded."""

    components: list[Component]


@dataclass
class Assignment:
    """
    Representation of an assignment statement.

    - ordinarily one value to a single target
    - multiple targets when chain assigning (a = b = c)

    Target or value may be None if not trackable.
    """

    targets: list[PendingAccess | None]
    value: PendingAccess | None


class NameBreak(str, Enum):
    """
    Elements that break name access chains.

    The symbols are arbitrary, only avoiding being valid Python names
    in order to not clash with actual named components in the chain.
    """

    call = "()"
    namedexpr = ":="
    import_from = ">"


class LinkContext(str, Enum):
    """Context in which a link appears to help HTML matching."""

    none = "none"
    after_call = "after_call"
    import_from = "import_from"  # from *mod.sub* import foo
    import_target = "import_target"  # from mod.sub import *foo*


@dataclass
class Name:
    """A name accessed in the source traced back to an import."""

    import_components: list[str]
    code_str: str
    lineno: int
    end_lineno: int
    context: LinkContext | None = None
    resolved_location: str | None = None


@dataclass
class Access:
    """
    Accessed import, whose tail is about to be recorded as a Name.

    :attr:`prior_components` are components that are implicitly used via
    the base name in :attr:`components`, which is the part that shows on the line.
    The base component that connects an import to the name that was used to
    access it is automatically removed from the components in :attr:`full_components`.
    """

    context: LinkContext
    prior_components: list[Component]
    components: list[Component]

    @property
    def full_components(self) -> list[Component]:
        """All components from import base to used components."""
        if not self.prior_components:
            # Import statement itself
            return self.components

        return self.prior_components + self.components[1:]

    @property
    def lineno_span(self) -> tuple[int, int]:
        """Estimate the lineno span of components."""
        min_ = min(c.lineno for c in self.components)
        max_ = max(c.end_lineno for c in self.components)
        return min_, max_

    def to_name(self) -> Name:
        """Convert access tail (from a break) into a Name."""
        components = [
            c.name
            for c in self.full_components
            if c.name not in (NameBreak.import_from, NameBreak.namedexpr)
        ]

        breaks = [i for i, c in enumerate(self.components) if c.name in list(NameBreak)]
        start_ix = breaks[-1] + 1 if breaks else 0
        code_str = ".".join(c.name for c in self.components[start_ix:])

        if breaks and self.components[breaks[-1]].name == NameBreak.call:
            context = LinkContext.after_call
        else:
            context = self.context

        return Name(components, code_str, *self.lineno_span, context=context)


builtin_components: dict[str, list[Component]] = {
    b: [Component(b, -1, -1, LinkContext.none)] for b in dir(builtins)
}


class ImportTrackerVisitor(ast.NodeVisitor):
    """Track imports and their use through source code."""

    def __init__(self, doctree_node) -> None:
        super().__init__()
        self.doctree_node = doctree_node
        self.accessed: list[Name] = []
        self.in_augassign = False
        self._is_chaining = 0

        # Stack for dealing with class body pseudo scopes
        # which are completely bypassed by inner scopes (func, lambda).
        # Current values are copied to the next class body level.
        self.pseudo_scopes_stack: list[dict[str, list[Component]]] = [
            builtin_components.copy()
        ]
        # Stack for dealing with nested scopes.
        # Holds references to the values of previous nesting levels.
        self.outer_scopes_stack: list[dict[str, list[Component]]] = []

    @property
    def current_locals(self):
        """Get the current local variables and their component chains."""
        return self.pseudo_scopes_stack[-1]

    def save_accessed_names(self, access: Access) -> None:
        """Convert Access to Names to store in the visitor for aggregation."""
        self.accessed.append(access.to_name())

    def visit(self, node: ast.AST) -> PendingAccess | None:
        """
        Override default visit to track name access and assignments.

        Only ast.Name and ast.Attribute form unbroken access chains.
        We make sure those are processed unbroken first. After reaching
        the end of the chain (or when encountering an assignment),
        the access chains and assignments are resolved.
        """
        self._is_chaining, was_chaining = (
            isinstance(node, ast.Name | ast.Attribute),
            self._is_chaining,
        )
        result: Assignment | PendingAccess | None = super().visit(node)

        if isinstance(result, PendingAccess) and self._is_chaining and not was_chaining:
            result = self.resolve_pending_access(result)
        elif isinstance(result, Assignment):
            self.resolve_assignment(result)
            result = None

        self._is_chaining = was_chaining
        return result

    def overwrite_name(self, name: str) -> None:
        """Overwrite name in current scope."""
        # Technically dotted values could now be bricked,
        # but we can't prevent the earlier values in the chain from being used.
        # There is a chance that the value which was assigned is a something
        # that we could follow, but for now it's not really worth the effort.
        # With a dotted value, the following condition will never hold as long
        # as the dotted components of imports are discarded on creating the import.
        self.current_locals.pop(name, None)

    def assign_name(self, name: str, components: list[Component]) -> None:
        """Import or assign a name to current scope."""
        # Overwriting technically unnecessary until it properly follows dots
        self.overwrite_name(name)
        for c in components:
            c.context = "load"

        prev_comps = self.current_locals.get(components[0].name)
        if prev_comps:
            components = prev_comps + components[1:]
        self.current_locals[name] = components

    def _create_access(self, components: list[Component]) -> PendingAccess | None:
        """Create access from scope."""
        scope_key = components[0].name
        prior = self.current_locals.get(scope_key)
        if prior is None:
            return None

        access = Access(LinkContext.none, prior, components)
        self.save_accessed_names(access)
        return PendingAccess(components=components)

    def resolve_pending_access(self, pending: PendingAccess) -> PendingAccess | None:
        """Resolve and save pending access."""
        components = pending.components

        context = components[0].context
        if context == "store" and not self.in_augassign:
            self.overwrite_name(components[0].name)
            return pending

        access = self._create_access(components)
        if context == "del":
            self.overwrite_name(components[0].name)
        return access

    def resolve_assignment(self, assignment: Assignment) -> None:
        """Resolve access for assignment values and targets."""
        for target in assignment.targets:
            self.resolve_single_assign_target(target, assignment.value)

    def resolve_single_assign_target(
        self, target: PendingAccess | None, value: PendingAccess | None
    ) -> None:
        """Assign value to a single assignment target."""
        if target is None:
            return

        if len(target.components) == 1:
            comp = target.components[0]
            if value is None:
                self.overwrite_name(comp.name)
            else:
                self.assign_name(comp.name, value.components)
                self._create_access(target.components)
        else:
            self.resolve_pending_access(target)

    def create_simple_access(self, name: str, lineno: int) -> None:
        """Create single-component access to scope."""
        component = Component(name, lineno, lineno, "load")
        self._create_access([component])

    def visit_Global(self, node: ast.Global) -> None:
        """Import from top scope."""
        if not self.outer_scopes_stack:
            return  # in outermost scope already, no-op for imports

        imports = self.outer_scopes_stack[0]
        for name in node.names:
            self.overwrite_name(name)
            if name in imports:
                self.assign_name(name, imports[name])
                self.create_simple_access(name, node.lineno)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        """Import from intermediate scopes."""
        imports_stack = self.outer_scopes_stack[1:]
        for name in node.names:
            self.overwrite_name(name)
            for imports in imports_stack[::-1]:
                if name in imports:
                    self.assign_name(name, imports[name])
                    self.create_simple_access(name, node.lineno)
                    break

    def visit_Import(self, node: ast.Import | ast.ImportFrom, prefix: str = "") -> None:
        """Register import source."""
        import_star = node.names[0].name == "*"
        if import_star:
            try:
                mod = import_module(node.module)
                import_names = [
                    name for name in mod.__dict__ if not name.startswith("_")
                ]
                aliases = [None] * len(import_names)
            except ImportError:
                logger.warning(
                    f"Could not import module `{node.module}` for parsing!",
                    type=warn_type,
                    subtype="import_star",
                    location=self.doctree_node,
                )
                import_names = []
                aliases = []
        else:
            import_names = [name.name for name in node.names]
            aliases = [name.asname for name in node.names]

        prefix_parts = prefix.rstrip(".").split(".") if prefix else []
        prefix_components = [Component(n, *linenos(node), "load") for n in prefix_parts]
        if prefix_components:
            self.save_accessed_names(
                Access(LinkContext.import_from, [], prefix_components)
            )
            prefix_components.append(
                Component(NameBreak.import_from, *linenos(node), "load")
            )

        for import_name, alias in zip(import_names, aliases, strict=True):
            if not import_star:
                components = [
                    Component(n, *linenos(node), "load") for n in import_name.split(".")
                ]
                self.save_accessed_names(
                    Access(
                        LinkContext.import_target, [], prefix_components + components
                    )
                )

            if not alias and "." in import_name:
                # equivalent to only import top level module since we don't
                # follow assignments and the outer modules also get imported
                import_name = import_name.split(".")[0]  # noqa: PLW2901

            full_components = [
                Component(n, *linenos(node), "store")
                for n in (prefix + import_name).split(".")
            ]
            self.assign_name(alias or import_name, full_components)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Register import source."""
        if node.level:  # relative import
            for name in node.names:
                self.overwrite_name(name.asname or name.name)
        else:
            self.visit_Import(node, prefix=node.module + ".")

    def visit_Name(self, node: ast.Name) -> PendingAccess:
        """Create the initial pending access chain."""
        return PendingAccess([Component.from_ast(node)])

    def visit_Attribute(self, node: ast.Attribute) -> PendingAccess | None:
        """Add attribute access to an existing access chain."""
        inner: PendingAccess | None = self.visit(node.value)
        if inner is not None:
            inner.components.append(Component.from_ast(node))
        return inner

    def visit_Call(self, node: ast.Call) -> PendingAccess | None:
        """Add call to an existing access chain and separately visit args."""
        inner: PendingAccess | None = self.visit(node.func)
        if inner is not None:
            inner.components.append(Component.from_ast(node))
        for arg in node.args + node.keywords:
            self.visit(arg)
        return inner

    def visit_Tuple(self, node: ast.Tuple) -> None:
        """Override stored values as tuple assignment is not supported."""
        for element in node.elts:
            result = self.visit(element)
            if isinstance(node.ctx, ast.Store) and isinstance(result, PendingAccess):
                self.resolve_single_assign_target(result, None)

    def visit_Assign(self, node: ast.Assign) -> Assignment:
        """Visit an Assign node."""
        value = self.visit(node.value)
        targets = []
        for n in node.targets[::-1]:
            target = self.visit(n)
            targets.append(target)
        return Assignment(targets, value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Assignment:
        """Visit an AnnAssign node."""
        value = self.visit(node.value) if node.value is not None else None
        annot = self.visit(node.annotation)
        if annot is not None:
            annot.components.append(
                Component(NameBreak.call, *linenos(node.annotation), "load")
            )
            value = annot

        target = self.visit(node.target)
        return Assignment([target], value)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """Visit an AugAssign node."""
        self.visit(node.value)
        self.in_augassign, temp = (True, self.in_augassign)
        self.visit(node.target)
        self.in_augassign = temp

    def visit_NamedExpr(self, node: ast.NamedExpr) -> PendingAccess:
        """Visit a NamedExpr node."""
        value = self.visit(node.value)
        target = self.visit(node.target)
        assign = Assignment([target], value)
        self.resolve_assignment(assign)
        if value is not None:
            value.components.append(Component.from_ast(node))
        return value

    def visit_MatchClass(self, node: ast.AST) -> None:
        """Visit a match case class as a series of assignments."""
        cls = self.visit(node.cls)

        pattern_accesses = []
        for n in node.patterns:
            access = self.visit(n)
            if access is not None:
                pattern_accesses.append(access)

        kwd_accesses = []
        for attr in node.kwd_attrs:
            if cls is None:
                kwd_accesses.append(None)
                continue

            attr_comps = [
                Component(NameBreak.call, *linenos(node), "load"),
                Component(attr, *linenos(node), "load"),
            ]
            access = PendingAccess(cls.components + attr_comps)
            kwd_accesses.append(access)

        for access in pattern_accesses + kwd_accesses:
            if access is not None:
                self.resolve_pending_access(access)

        assigns = []
        for access, pattern in zip(kwd_accesses, node.kwd_patterns, strict=True):
            target = self.visit(pattern)
            if cls is not None and target is not None:
                assigns.append(Assignment([target], access))

        for assign in assigns:
            self.resolve_assignment(assign)

    def visit_MatchAs(self, node: ast.AST) -> PendingAccess | None:
        """Track match alias names."""
        if node.name is None:
            return None
        return PendingAccess([Component.from_ast(node)])

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        """Delegate to sync for."""
        self.visit_For(node)

    def visit_For(self, node: ast.For | ast.AsyncFor) -> None:
        """Swap node order."""
        self.visit(node.iter)
        self.visit(node.target)
        for n in node.body:
            self.visit(n)
        for n in node.orelse:
            self.visit(n)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
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

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Delegate to func def."""
        self.visit_FunctionDef(node)

    @staticmethod
    def _get_args(node: ast.arguments) -> list[ast.arg]:
        return node.args + node.kwonlyargs + node.posonlyargs

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
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

    def visit_arg(self, arg: ast.arg) -> Assignment:
        """Handle function argument and its annotation."""
        target = PendingAccess([Component.from_ast(arg)])
        if arg.annotation is not None:
            value = self.visit(arg.annotation)
            if value is not None:
                value.components.append(
                    Component(NameBreak.call, *linenos(arg), "load")
                )
        else:
            value = None
        return Assignment([target], value)

    def visit_Lambda(self, node: ast.Lambda) -> None:
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

    def visit_ListComp(self, node: ast.ListComp) -> None:
        """Delegate to generic comp."""
        self.visit_generic_comp([node.elt], node.generators)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        """Delegate to generic comp."""
        self.visit_generic_comp([node.elt], node.generators)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        """Delegate to generic comp."""
        self.visit_generic_comp([node.key, node.value], node.generators)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        """Delegate to generic comp."""
        self.visit_generic_comp([node.elt], node.generators)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        """Swap node order."""
        self.visit(node.iter)
        self.visit(node.target)
        for f in node.ifs:
            self.visit(f)

    def visit_generic_comp(
        self, values: list[ast.AST], generators: list[ast.comprehension]
    ) -> None:
        """Separate inner scope, respects class body scope."""
        inner = self.__class__(self.doctree_node)
        inner.pseudo_scopes_stack[0] = self.current_locals.copy()
        for gen in generators:
            inner.visit(gen)
        for value in values:
            inner.visit(value)
        self.accessed.extend(inner.accessed)
