"""
Use pseudo lambda calculus style functional application to reduce boolean expressions for faster computation. Define rules in ruleCFG.json
"""
import json
from dataclasses import dataclass
from re import match

"""
Dont mess with anything that says dataclass frozen=True
"""

@dataclass(frozen=True)
class Expr:
    def __and__(self, other):
        return And((self, other))

    def __or__(self, other):
        return Or((self, other))

    def __invert__(self):
        return Not(self)

    def __xor__(self, other):
        return Xor((self, other))

@dataclass(frozen=True)
class Var(Expr):
    name: str

@dataclass(frozen=True)
class Const(Expr):
    value: bool

@dataclass(frozen=True)
class Not(Expr):
    x: Expr

@dataclass(frozen=True)
class And(Expr):
    xs: tuple[Expr, ...]

@dataclass(frozen=True)
class Or(Expr):
    xs: tuple[Expr, ...]

@dataclass(frozen=True)
class Xor(Expr):
    xs: tuple[Expr, ...]


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: Expr
    replace: Expr

def load_rules(filename: str) -> list[Rule]:
    """Load rules from a JSON file.

    Args:
        filename (str): The path to the JSON file containing the rules.

    Returns:
        list[Rule]: A list of Rule objects loaded from the JSON file.
    """
    with open(filename, "r") as file:
        data = json.load(file)

    rules = []

    for item in data:
        rules.append(
            Rule(
                name=item["name"],
                pattern=parse(item["pattern"]),
                replace=parse(item["replace"]),
            )
        )

    return rules


def expr_to_string(expr: Expr) -> str:
    """Render an expression back into the project’s Boolean formula syntax."""
    if isinstance(expr, Var):
        return expr.name

    if isinstance(expr, Const):
        return "1" if expr.value else "0"

    if isinstance(expr, Not):
        inner = expr_to_string(expr.x)
        if isinstance(expr.x, (And, Or, Xor)):
            return f"~{inner}"
        return f"~{inner}"

    if isinstance(expr, And):
        return f"({' & '.join(expr_to_string(item) for item in expr.xs)})"

    if isinstance(expr, Or):
        return f"({' | '.join(expr_to_string(item) for item in expr.xs)})"

    if isinstance(expr, Xor):
        return f"({' ^ '.join(expr_to_string(item) for item in expr.xs)})"

    raise TypeError(f"Unknown expression: {expr}")


def _combine_associative(op: type[And] | type[Or] | type[Xor], left: Expr, right: Expr):
    """Flatten repeated associative operators into a single tuple-based node."""
    terms: list[Expr] = []
    for operand in (left, right):
        if isinstance(operand, op):
            terms.extend(operand.xs)
        else:
            terms.append(operand)
    return op(tuple(terms))


def parse(text: str) -> Expr:
    """Parse a boolean expression from a string.

    Args:
        text (str): The string representation of the boolean expression.

    Returns:
        Expr: The parsed boolean expression as an Expr object.
    """
    text = text.replace(" ", "")

    if text.startswith("(") and text.endswith(")"):
        depth = 0
        matches = True
        for i, char in enumerate(text):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0 and i != len(text) - 1:
                    matches = False
                    break
        if matches:
            text = text[1:-1]

    # OR < XOR < AND
    depth = 0

    for i in range(len(text) - 1, -1, -1):
        char = text[i]
        if char == ")":
            depth += 1
        elif char == "(":
            depth -= 1
        elif depth == 0:
            if char == "|":
                return _combine_associative(Or, parse(text[:i]), parse(text[i + 1:]))
            elif char == "^":
                return _combine_associative(Xor, parse(text[:i]), parse(text[i + 1:]))
            elif char == "&":
                return _combine_associative(And, parse(text[:i]), parse(text[i + 1:]))

    if text.startswith("~"):
        return Not(parse(text[1:]))

    if text == "0":
        return Const(False)
    elif text == "1":
        return Const(True)
    else:
        return Var(text)

    raise ValueError(f"Invalid expression: {text}")

def _combine_expression(parts: tuple[Expr, ...], op: type[And] | type[Or] | type[Xor]) -> Expr:
    if len(parts) == 1:
        return parts[0]
    return op(parts)


def _match_associative(pattern_terms: tuple[Expr, ...], expr_terms: tuple[Expr, ...], bindings: dict[str, Expr], op: type[And] | type[Or] | type[Xor]):
    if len(pattern_terms) == 0:
        return bindings if not expr_terms else None
    if len(pattern_terms) == 1:
        if len(expr_terms) == 1:
            return matching_engine(pattern_terms[0], expr_terms[0], bindings)
        return matching_engine(pattern_terms[0], _combine_expression(expr_terms, op), bindings)

    for split in range(1, len(expr_terms) - len(pattern_terms) + 2):
        left = expr_terms[:split]
        right = expr_terms[split:]
        first_pattern = pattern_terms[0]
        rest_pattern = pattern_terms[1:]
        left_expr = _combine_expression(left, op)
        if len(right) < len(rest_pattern):
            continue
        new_bindings = matching_engine(first_pattern, left_expr, bindings)
        if new_bindings is None:
            continue
        if len(rest_pattern) == 0:
            return new_bindings
        result = _match_associative(rest_pattern, right, new_bindings, op)
        if result is not None:
            return result
    return None


def matching_engine(pattern: Expr, expr: Expr, bindings=None):
    """Match a pattern against an expression and return variable bindings.

    Args:
        pattern (Expr): The pattern expression, potentially containing placeholders.
        expr (Expr): The expression to match against the pattern.
        bindings (dict, optional): Existing variable bindings. Defaults to None.

    Returns:
        dict or None: A dictionary of variable bindings if the pattern matches the expression, otherwise None.
    """
    if bindings is None:
        bindings = {}

    # identify placeholders they are always lowercase
    if isinstance(pattern, Var) and pattern.name.islower():
        if pattern.name in bindings:
            if bindings[pattern.name] == expr:
                return bindings
            return None

        bindings[pattern.name] = expr
        return bindings
    
    if isinstance(pattern, Var) or isinstance(pattern, Const):
        if pattern == expr:
            return bindings
        return None

    if isinstance(pattern, Not):
        if not isinstance(expr, Not):
            return None
        return matching_engine(pattern.x, expr.x, bindings)

    if isinstance(pattern, And):
        if not isinstance(expr, And):
            return None
        return _match_associative(pattern.xs, expr.xs, bindings, And)

    if isinstance(pattern, Or):
        if not isinstance(expr, Or):
            return None
        return _match_associative(pattern.xs, expr.xs, bindings, Or)

    if isinstance(pattern, Xor):
        if not isinstance(expr, Xor):
            return None
        return _match_associative(pattern.xs, expr.xs, bindings, Xor)
    
    return None

def substitute_variables(expr: Expr, bindings: dict[str, Expr]) -> Expr:
    """Substitute variables in an expression based on the given bindings.

    Args:
        expr (Expr): The expression in which to substitute variables.
        bindings (dict[str, Expr]): A dictionary mapping variable names to expressions.

    Returns:
        Expr: The expression with variables substituted according to the bindings.
    """

    if isinstance(expr, Var):
        if expr.name in bindings:
            return bindings[expr.name]
        return expr
    
    if isinstance(expr, Const):
        return expr

    if isinstance(expr, Not):
        return Not(substitute_variables(expr.x, bindings))

    if isinstance(expr, And):
        return And(tuple(substitute_variables(x, bindings) for x in expr.xs))

    if isinstance(expr, Or):
        return Or(tuple(substitute_variables(x, bindings) for x in expr.xs))

    if isinstance(expr, Xor):
        return Xor(tuple(substitute_variables(x, bindings) for x in expr.xs))

    raise TypeError(f"Unknown expression: {expr}")

def apply_rule(expr: Expr, rule: Rule) -> Expr:
    """Apply a single rule to an expression.

    Args:
        expr (Expr): The expression to which the rule should be applied.
        rule (Rule): The rule to apply.

    Returns:
        Expr: The resulting expression after applying the rule, or None if the rule does not match.
    """
    bindings = matching_engine(rule.pattern, expr)
    if bindings is None:
        return None

    return substitute_variables(rule.replace, bindings)

def apply_rules(expr: Expr, rules: list[Rule]) -> Expr:
    """Apply a list of rules to an expression.

    Args:
        expr (Expr): The expression to which the rules should be applied.
        rules (list[Rule]): A list of rules to apply.

    Returns:
        Expr: The resulting expression after applying the first matching rule, or the original expression if no rules match.
    """
    for rule in rules:
        new_expr = apply_rule(expr, rule)
        if new_expr is not None:
            return new_expr
    return expr

def simplify(expr: Expr, rules: list[Rule]) -> Expr:
    """Simplify an expression by repeatedly applying a set of rules.

    Args:
        expr (Expr): The expression to simplify.
        rules (list[Rule]): A list of rules to use for simplification.

    Returns:
        Expr: The simplified expression.
    """

    if isinstance(expr, Not):
        expr = Not(simplify(expr.x, rules))

    elif isinstance(expr, And):
        expr = And(tuple(simplify(x, rules) for x in expr.xs))
    elif isinstance(expr, Or):
        expr = Or(tuple(simplify(x, rules) for x in expr.xs))
    elif isinstance(expr, Xor):
        expr = Xor(tuple(simplify(x, rules) for x in expr.xs))

    while True:
        result = apply_rules(expr, rules)

        if result is None or result == expr:
            break
        expr = result

    return expr