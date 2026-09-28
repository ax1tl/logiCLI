"""
Use pseudo lambda calculus style functional application to reduce boolean expressions for faster computation. Define rules in ruleCFG.json
"""
import json
from dataclasses import dataclass
from re import match


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
    bindings = matching_engine(rule.pattern, expr)
    if bindings is None:
        return None

    return substitute_variables(rule.replace, bindings)

def apply_rules(expr: Expr, rules: list[Rule]) -> Expr:
    for rule in rules:
        new_expr = apply_rule(expr, rule)
        if new_expr is not None:
            return new_expr
    return expr

def simplify(expr: Expr, rules: list[Rule]) -> Expr:

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