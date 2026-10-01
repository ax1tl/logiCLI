"""
Use pseudo lambda calculus style functional application to reduce boolean expressions for faster computation. Define rules in ruleCFG.json
"""
import json
from dataclasses import dataclass
from functools import lru_cache
from itertools import product
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
    """Render an expression back into the project's Boolean formula syntax."""
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

def _flatten_associative(expr: Expr, op: type[And] | type[Or] | type[Xor]) -> tuple[Expr, ...]:
    if isinstance(expr, op):
        return tuple(term for child in expr.xs for term in _flatten_associative(child, op))
    return (expr,)

def _rewrite_associative_subexpression(expr: And | Or | Xor, rules: list[Rule]) -> Expr:
    op = type(expr)
    for start in range(len(expr.xs)):
        for end in range(start + 2, len(expr.xs) + 1):
            candidate = _combine_expression(expr.xs[start:end], op)
            replacement = apply_rules(candidate, rules)
            if replacement == candidate:
                continue

            replacement_terms = replacement.xs if isinstance(replacement, op) else (replacement,)
            terms = tuple(
                term
                for item in expr.xs[:start] + replacement_terms + expr.xs[end:]
                for term in _flatten_associative(item, op)
            )
            return _combine_expression(terms, op)

    return expr

def simplify(expr: Expr, rules: list[Rule]) -> Expr:
    """Simplify an expression by repeatedly applying a set of rules.

    Args:
        expr (Expr): The expression to simplify.
        rules (list[Rule]): A list of rules to use for simplification.

    Returns:
        Expr: The simplified expression.
    """

    minimized = _minimize_boolean_expression(expr)
    rewritten = _simplify_with_rules(minimized, rules)
    if rewritten == minimized:
        return minimized
    return _minimize_boolean_expression(rewritten)


def _simplify_with_rules(expr: Expr, rules: list[Rule]) -> Expr:
    if isinstance(expr, Not):
        expr = Not(_simplify_with_rules(expr.x, rules))

    elif isinstance(expr, And):
        expr = And(tuple(_simplify_with_rules(x, rules) for x in expr.xs))
    elif isinstance(expr, Or):
        expr = Or(tuple(_simplify_with_rules(x, rules) for x in expr.xs))
    elif isinstance(expr, Xor):
        expr = Xor(tuple(_simplify_with_rules(x, rules) for x in expr.xs))

    while True:
        result = apply_rules(expr, rules)

        if result is not None and result != expr:
            expr = _simplify_with_rules(result, rules)
            continue

        if isinstance(expr, (And, Or, Xor)):
            result = _rewrite_associative_subexpression(expr, rules)
            if result != expr:
                expr = _simplify_with_rules(result, rules)
                continue

        break

    return expr


def _evaluate_expression(expr: Expr, values: dict[str, bool]) -> bool:
    if isinstance(expr, Var):
        return values[expr.name]
    if isinstance(expr, Const):
        return expr.value
    if isinstance(expr, Not):
        return not _evaluate_expression(expr.x, values)
    if isinstance(expr, And):
        return all(_evaluate_expression(item, values) for item in expr.xs)
    if isinstance(expr, Or):
        return any(_evaluate_expression(item, values) for item in expr.xs)
    if isinstance(expr, Xor):
        return sum(_evaluate_expression(item, values) for item in expr.xs) % 2 == 1
    raise TypeError(f"Unknown expression: {expr}")


def _collect_variables(expr: Expr) -> set[str]:
    if isinstance(expr, Var):
        return {expr.name}
    if isinstance(expr, Const):
        return set()
    if isinstance(expr, Not):
        return _collect_variables(expr.x)
    if isinstance(expr, (And, Or, Xor)):
        return set().union(*(_collect_variables(item) for item in expr.xs))
    raise TypeError(f"Unknown expression: {expr}")


def _make_not(expr: Expr) -> Expr:
    if isinstance(expr, Const):
        return Const(not expr.value)
    if isinstance(expr, Not):
        return expr.x
    return Not(expr)


def _make_and(terms: tuple[Expr, ...]) -> Expr:
    flattened = tuple(term for item in terms for term in _flatten_associative(item, And))
    if any(isinstance(term, Const) and not term.value for term in flattened):
        return Const(False)
    remaining = tuple(
        term for term in flattened if not isinstance(term, Const) or term.value
    )
    if any(_make_not(term) in remaining for term in remaining):
        return Const(False)
    unique = tuple(dict.fromkeys(remaining))
    if not unique:
        return Const(True)
    return _combine_expression(unique, And)


def _make_or(terms: tuple[Expr, ...]) -> Expr:
    flattened = tuple(term for item in terms for term in _flatten_associative(item, Or))
    if any(isinstance(term, Const) and term.value for term in flattened):
        return Const(True)
    remaining = tuple(
        term for term in flattened if not isinstance(term, Const) or not term.value
    )
    if any(_make_not(term) in remaining for term in remaining):
        return Const(True)
    unique = tuple(dict.fromkeys(remaining))
    if not unique:
        return Const(False)
    return _combine_expression(unique, Or)


def _make_xor(terms: tuple[Expr, ...]) -> Expr:
    flattened = tuple(term for item in terms for term in _flatten_associative(item, Xor))
    inverted = sum(
        term.value for term in flattened if isinstance(term, Const)
    ) % 2 == 1
    counts: dict[Expr, bool] = {}
    ordered_terms: list[Expr] = []
    for term in flattened:
        if isinstance(term, Const):
            continue
        if term not in counts:
            ordered_terms.append(term)
        counts[term] = not counts.get(term, False)
    remaining = tuple(term for term in ordered_terms if counts[term])
    if not remaining:
        return Const(inverted)
    result = _combine_expression(remaining, Xor)
    return _make_not(result) if inverted else result


def _minimize_boolean_expression(expr: Expr) -> Expr:
    """Find a shorter equivalent expression for formulas with at most 8 variables."""
    variable_names = tuple(sorted(_collect_variables(expr)))
    if not variable_names or len(variable_names) > 8:
        return expr

    assignments = tuple(product((False, True), repeat=len(variable_names)))
    truth_values = tuple(
        _evaluate_expression(expr, dict(zip(variable_names, assignment)))
        for assignment in assignments
    )

    @lru_cache(maxsize=None)
    def best_expression(remaining: tuple[str, ...], values: tuple[bool, ...]) -> Expr:
        if all(value == values[0] for value in values):
            return Const(values[0])

        assignment_rows = tuple(product((False, True), repeat=len(remaining)))
        candidates: list[Expr] = []

        for index, name in enumerate(remaining):
            reduced_variables = remaining[:index] + remaining[index + 1:]
            low_values = tuple(
                value
                for row, value in zip(assignment_rows, values)
                if not row[index]
            )
            high_values = tuple(
                value
                for row, value in zip(assignment_rows, values)
                if row[index]
            )

            if low_values == high_values:
                candidates.append(best_expression(reduced_variables, low_values))
                continue

            low_expr = best_expression(reduced_variables, low_values)
            high_expr = best_expression(reduced_variables, high_values)
            variable = Var(name)

            if all(low != high for low, high in zip(low_values, high_values)):
                candidates.append(_make_xor((variable, low_expr)))

            if not any(low_values):
                candidates.append(_make_and((variable, high_expr)))
            elif not any(high_values):
                candidates.append(_make_and((_make_not(variable), low_expr)))
            elif all(low_values):
                candidates.append(_make_or((_make_not(variable), high_expr)))
            elif all(high_values):
                candidates.append(_make_or((variable, low_expr)))
            else:
                candidates.append(
                    _make_or(
                        (
                            _make_and((_make_not(variable), low_expr)),
                            _make_and((variable, high_expr)),
                        )
                    )
                )

        return min(
            candidates,
            key=lambda candidate: (len(expr_to_string(candidate)), expr_to_string(candidate)),
        )

    minimized = best_expression(variable_names, truth_values)
    if len(expr_to_string(minimized)) < len(expr_to_string(expr)):
        return minimized
    return expr