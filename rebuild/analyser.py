
import re


class RegexNode:
    def optimised(self) -> "RegexNode":
        return self

    def regex(self, as_atom=False) -> str:
        return ""

    def __bool__(self):
        return True

    def as_json(self):
        # Automatically generate a tree structure for this object

        def json_for(value):
            """Creates a json like structure for the given object """
            if isinstance(value, RegexNode):
                if type(value) is EmptyNode:
                    return None
                return value.as_json()

            if type(value) in (list, tuple):
                return [json_for(item) for item in value]

            if type(value) is str:
                return "\"" + value + "\""

            return str(value)

        def prettify_varname(name):
            return name.replace("_", " ").title()

        def prettify_classname(name):
            return re.sub(r"(?<=[a-z])([A-Z])", r" \1", name)

        # Find all properties / fields of the object
        fields = [field for field in vars(self) if not field.startswith("_")]

        name = prettify_classname(self.__class__.__name__)

        # E.g. for EmptyNode
        if len(fields) == 0:
            return name

        # If there is only one field, then ignore the name of the field
        if len(fields) == 1:
            value = getattr(self, fields[0])
            subtree = json_for(value)

            if type(subtree) is str:
                return name + ": " + subtree

            return {name: subtree}

        subtree = {}

        for field in fields:
            value = getattr(self, field)
            value_json = json_for(value)

            if value_json is None:
                # EmptyNode
                subtree[prettify_varname(field) + ": ---"] = None

            elif type(value_json) is str:
                subtree[prettify_varname(field) + ": " + value_json] = None
            else:
                subtree[prettify_varname(field)] = value_json

        return {name: subtree}

    def pretty_print(self):
        tree = self.as_json()
        _print_pretty_tree(tree)


def _ipretty_tree(tree, depth=0):
    indentation = "|   " * depth

    if type(tree) is list:
        for item in tree:
            yield from _ipretty_tree(item, depth)
        return

    if type(tree) is dict:
        for name, subtree in tree.items():
            yield indentation + name
            if (type(subtree) is str and len(subtree) == 0) or subtree is None:
                continue
            yield from _ipretty_tree(subtree, depth + 1)
        return

    yield indentation + str(tree)


def _print_pretty_tree(tree, depth=0):
    indentation = "|   " * depth

    if type(tree) is list:
        for item in tree:
            _print_pretty_tree(item, depth)
        return

    if type(tree) is dict:
        for name, subtree in tree.items():
            print(indentation + name)
            if (type(subtree) is str and len(subtree) == 0) or subtree is None:
                continue
            _print_pretty_tree(subtree, depth+1)
        return

    print(indentation + str(tree))


class EmptyNode (RegexNode):
    def as_json(self):
        return "Empty"

    def __bool__(self):
        return False


class Sequence (RegexNode):
    def __init__(self, items):
        self.items = items

    def optimised(self) -> "RegexNode":
        optimised = [item.optimised() for item in self.items]
        non_empty = list(filter(None, optimised))

        if len(non_empty) == 0:
            return EmptyNode()

        if len(non_empty) == 1:
            return non_empty[0]

        return Sequence(non_empty)

    def regex(self, as_atom=False) -> str:
        pattern = "".join(item.regex() for item in self.items)
        if as_atom:
            return "(?:" + pattern + ")"
        return pattern


# TODO: Add optimisations (Look at the either() in previous version in rebuild.py)
# TODO: Optimise nested either blocks (that do not capture!)
# TODO: Handle negative char sets [^...]
class Alternation (RegexNode):
    def __init__(self, options):
        self.options = options

    def optimised(self) -> "RegexNode":
        optimised = [item.optimised() for item in self.options]
        return Alternation(optimised)

    def regex(self, as_atom=False, is_root=False) -> str:
        pattern = "|".join(option.regex() for option in self.options)

        if is_root:
            return pattern
        return f"(?:{pattern})"


class SingleChar (RegexNode):
    def __init__(self, char):
        self.char = char

    def regex(self, as_atom=False) -> str:
        return self.char


class OneOrMore (RegexNode):
    def __init__(self, pattern, is_lazy=False):
        self.is_lazy = is_lazy
        self.pattern = pattern

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()

        optimised = self.pattern.optimised()
        return OneOrMore(optimised, self.is_lazy)

    def regex(self, as_atom=False) -> str:
        if type(self.pattern) is EmptyNode:
            return ""

        regex = self.pattern.regex(as_atom=True) + "+"

        if self.is_lazy:
            regex += "?"

        if as_atom:
            return f"(?:{regex})"

        return regex


class ZeroOrMore (RegexNode):
    def __init__(self, pattern, is_lazy=False):
        self.is_lazy = is_lazy
        self.pattern = pattern

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()

        optimised = self.pattern.optimised()
        return ZeroOrMore(optimised, self.is_lazy)

    def regex(self, as_atom=False) -> str:
        if type(self.pattern) is EmptyNode:
            return ""

        regex = self.pattern.regex(as_atom=True) + "*"

        if self.is_lazy:
            regex += "?"

        if as_atom:
            return f"(?:{regex})"

        return regex


class Optional (RegexNode):
    def __init__(self, pattern, is_lazy=False):
        self.is_lazy = is_lazy
        self.pattern = pattern

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()

        optimised = self.pattern.optimised()
        return Optional(optimised, self.is_lazy)

    def regex(self, as_atom=False) -> str:
        if type(self.pattern) is EmptyNode:
            return ""

        regex = self.pattern.regex(as_atom=True) + "?"

        if self.is_lazy:
            regex += "?"

        if as_atom:
            return f"(?:{regex})"

        return regex


class CapturingGroup (RegexNode):
    def __init__(self, pattern):
        self.pattern = pattern

    def optimised(self) -> "RegexNode":
        return CapturingGroup(self.pattern.optimised())

    def regex(self, as_atom=False) -> str:
        return f"({self.pattern.regex()})"


class NonCapturingGroup (RegexNode):
    def __init__(self, pattern):
        self.pattern = pattern

    def optimised(self) -> "RegexNode":
        return self.pattern.optimised()

    def regex(self, as_atom=False) -> str:
        return f"(?:{self.pattern.regex()})"


class NamedCapturingGroup (RegexNode):
    def __init__(self, name, pattern):
        self.name = name
        self.pattern = pattern

    def optimised(self) -> "RegexNode":
        return NamedCapturingGroup(self.name, self.pattern.optimised())

    def regex(self, as_atom=False) -> str:
        return f"(?P<{self.name}>{self.pattern.regex()})"


class ModeGroup (RegexNode):
    def __init__(self, modifiers, pattern):
        self.modifiers = modifiers
        self.pattern = pattern

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()

        if len(self.modifiers) == 0:
            return self.pattern.optimised()

        return ModeGroup(self.modifiers, self.pattern.optimised())

    def regex(self, as_atom=False) -> str:
        if type(self.pattern) is EmptyNode:
            return ""

        if len(self.modifiers) == 0:
            return self.pattern.regex(as_atom=as_atom)

        return f"(?{self.modifiers}:{self.pattern.regex()})"


class IfElseGroup (RegexNode):
    def __init__(self, name, then, elsewise):
        self.name = name
        self.then = then
        self.elsewise = elsewise

    def optimised(self) -> "RegexNode":
        if type(self.then) is EmptyNode and type(self.elsewise) is EmptyNode:
            return EmptyNode()
        return IfElseGroup(self.name, self.then.optimised(), self.elsewise.optimised())

    def regex(self, as_atom=False) -> str:
        return f"(?({self.name}){self.then.regex()}|{self.elsewise.regex()})"


class Lookaround (RegexNode):
    def __init__(self, pattern, symbol="="):
        self.pattern = pattern
        self._symbol = symbol

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()
        return Lookaround(self.pattern.optimised(), self._symbol)

    def regex(self, as_atom=False) -> str:
        return f"(?{self._symbol}{self.pattern.regex()})"


class Lookahead (Lookaround):
    def __init__(self, pattern):
        super().__init__(pattern, "=")


class NegativeLookahead (Lookaround):
    def __init__(self, pattern):
        super().__init__(pattern, "!")


class Lookbehind (Lookaround):
    def __init__(self, pattern):
        super().__init__(pattern, "<=")


class NegativeLookbehind (Lookaround):
    def __init__(self, pattern):
        super().__init__(pattern, "<!")


class AnchorStart (RegexNode):
    def regex(self, as_atom=False) -> str:
        return "^"


class AnchorEnd (RegexNode):
    def regex(self, as_atom=False) -> str:
        return "$"


# TODO: Add optimisation (Look at one_of of previous rebuild.py version)
class CharSet (RegexNode):
    def __init__(self, options):
        self.options = options

    def regex(self, as_atom=False) -> str:
        return f"[{''.join([option.regex() for option in self.options])}]"


# TODO: Add optimisation
class Range (RegexNode):
    def __init__(self, from_char, to_char):
        self.from_char = from_char
        self.to_char = to_char

    def optimised(self) -> "RegexNode":
        if self.from_char == self.to_char:
            return SingleChar(self.from_char)
        return self

    def regex(self, as_atom=False) -> str:
        return self.from_char + "-" + self.to_char


class RepeatExactlyN (RegexNode):
    def __init__(self, pattern, n, is_lazy=False):
        self.pattern = pattern
        self.n = n
        self.is_lazy = is_lazy

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()

        if self.n == 0:
            return EmptyNode()

        optimised = self.pattern.optimised()

        if self.n == 1:
            return optimised

        return RepeatExactlyN(optimised, self.n, self.is_lazy)

    def regex(self, as_atom=False) -> str:
        regex = self.pattern.regex(as_atom=True)

        if regex == "":
            return ""

        regex += "{" + str(self.n) + "}"

        if self.is_lazy:
            regex += "?"

        if as_atom:
            return "(?:" + regex + ")"
        return regex


class RepeatAtLeastN (RegexNode):
    def __init__(self, pattern, n, is_lazy):
        self.pattern = pattern
        self.n = n
        self.is_lazy = is_lazy

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()

        optimised = self.pattern.optimised()

        if self.n == 0:
            return ZeroOrMore(optimised)

        if self.n == 1:
            return OneOrMore(optimised)

        return RepeatAtLeastN(optimised, self.n, self.is_lazy)

    def regex(self, as_atom=False) -> str:
        regex = self.pattern.regex(as_atom=True)

        if regex == "":
            return ""

        regex += "{" + str(self.n) + ",}"

        if self.is_lazy:
            regex += "?"

        if as_atom:
            return "(?:" + regex + ")"
        return regex


class RepeatAtMostN (RegexNode):
    def __init__(self, pattern, n, is_lazy=False):
        self.pattern = pattern
        self.n = n
        self.is_lazy = is_lazy

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()

        if self.n == 0:
            return EmptyNode()

        optimised = self.pattern.optimised()

        if self.n == 1:
            return optimised

        return RepeatAtMostN(optimised, self.n, self.is_lazy)

    def regex(self, as_atom=False) -> str:
        regex = self.pattern.regex(as_atom=True)

        if regex == "":
            return ""

        regex += "{," + str(self.n) + "}"

        if self.is_lazy:
            regex += "?"

        if as_atom:
            return "(?:" + regex + ")"
        return regex


class RepeatBetweenNM (RegexNode):
    def __init__(self, pattern, n, m, is_lazy=False):
        self.pattern = pattern
        self.n = n
        self.m = m
        self.is_lazy = is_lazy

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()

        optimised = self.pattern.optimised()

        if self.n == self.m:
            return RepeatExactlyN(optimised, is_lazy=self.is_lazy)

        if self.m == 0:
            return EmptyNode()

        if self.m == 1:
            return Optional(optimised, is_lazy=self.n==0)

        return RepeatBetweenNM(optimised, self.n, self.m, self.is_lazy)

    def regex(self, as_atom=False) -> str:
        regex = self.pattern.regex(as_atom=True)

        if regex == "":
            return ""

        regex += "{" + str(self.n) + "," + str(self.m) + "}"

        if self.is_lazy:
            regex += "?"

        if as_atom:
            return "(?:" + regex + ")"
        return regex