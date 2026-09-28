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
                pattern=tuple(parse(expr) for expr in item["pattern"]),
                replace=tuple(parse(expr) for expr in item["replace"])
            )
        )

    return rules

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
                return Or((parse(text[:i]), parse(text[i + 1:])))
            elif char == "^":
                return Xor((parse(text[:i]), parse(text[i + 1:])))
            elif char == "&":
                return And((parse(text[:i]), parse(text[i + 1:])))

    if text.startswith("~"):
        return Not(parse(text[1:]))

    if text == "0":
        return Const(False)
    elif text == "1":
        return Const(True)
    else:
        return Var(text)

    raise ValueError(f"Invalid expression: {text}")

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
        return matching_engine(pattern.expr, expr.expr, bindings)

    if isinstance(pattern, And):
        if not isinstance(expr, And):
            return None

        if len(pattern.xs) != len(expr.xs):
            return None

        for p, e in zip(pattern.xs, expr.xs):
            bindings = matching_engine(p, e, bindings)

            if bindings is None:
                return None
        return bindings

    if isinstance(pattern, Or):
        if not isinstance(expr, Or):
            return None

        if len(pattern.xs) != len(expr.xs):
            return None

        for p, e in zip(pattern.xs, expr.xs):
            bindings = matching_engine(p, e, bindings)

            if bindings is None:
                return None
        return bindings

    if isinstance(pattern, Xor):
        if not isinstance(expr, Xor):
            return None

        if len(pattern.xs) != len(expr.xs):
            return None

        for p, e in zip(pattern.xs, expr.xs):
            bindings = matching_engine(p, e, bindings)

            if bindings is None:
                return None
        return bindings
    
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
        return Not(substitute_variables(expr.expr, bindings))

    if isinstance(expr, And):
        return And([substitute_variables(x, bindings) for x in expr.xs])

    if isinstance(expr, Or):
        return Or([substitute_variables(x, bindings) for x in expr.xs])

    if isinstance(expr, Xor):
        return Xor([substitute_variables(x, bindings) for x in expr.xs])

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
        expr = And([simplify(x, rules) for x in expr.xs])
    elif isinstance(expr, Or):
        expr = Or([simplify(x, rules) for x in expr.xs])
    elif isinstance(expr, Xor):
        expr = Xor([simplify(x, rules) for x in expr.xs])

    while True:
        result = apply_rules(expr, rules)

        if result is None or result == expr:
            break
        expr = result

    return expr