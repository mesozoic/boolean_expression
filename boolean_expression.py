"""
A basic library for representing boolean expressions, flattening them,
and converting them into strings for other puprposes.
"""

# MIT License
#
# Copyright (c) 2023 Alex Levy
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Iterable, Iterator, Tuple


class Condition:
    """
    A condition in a logical expression. Should not be created directly,
    but instead subclassed to extend behavior to something useful.
    """

    def __and__(self, other: Condition) -> Compound:
        """
        >>> lft = Expression('a')
        >>> rgt = Expression('b')
        >>> lft & rgt
        Compound('AND', [Expression('a'), Expression('b')])
        """
        return AND(self, other)

    def __or__(self, other: Condition) -> Compound:
        """
        >>> lft = Expression('a')
        >>> rgt = Expression('b')
        >>> lft | rgt
        Compound('OR', [Expression('a'), Expression('b')])
        """
        return OR(self, other)

    def __xor__(self, other: Condition) -> Compound:
        """
        >>> lft = Expression('a')
        >>> rgt = Expression('b')
        >>> lft ^ rgt
        Compound('OR',
         [Compound('AND', [Expression('a'), Compound('NOT', [Expression('b')])]),
          Compound('AND', [Expression('b'), Compound('NOT', [Expression('a')])])])
        """
        return OR(AND(self, NOT(other)), AND(other, NOT(self)))

    def __invert__(self) -> Compound:
        """
        >>> ~Expression('a')
        Compound('NOT', [Expression('a')])
        """
        return NOT(self)

    def flatten(self) -> Condition:
        """
        >>> c = Expression('a')
        >>> c.flatten() is c
        True
        """
        return self


class Expression(Condition):
    """
    Represents a logical expression that should not be quoted or escaped.

    >>> expr = Expression('LAST_MODIFIED_TIME() >= "2023-01-01"')
    >>> EQ("foo", 5) & expr
    Compound('AND', [EQ('foo', 5), Expression('LAST_MODIFIED_TIME() >= "2023-01-01"')])
    """

    def __init__(self, value: str) -> None:
        self.value = value

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value!r})"


@dataclass
class Comparison(Condition):
    """
    Represents a logical condition that matches a field to a value.
    Makes no assumptions about the meaning of a field or a value.
    """

    field: str
    value: Any

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.field!r}, {self.value!r})"


class EQ(Comparison):
    """
    Represents a logical condition that a field is equal to a value.
    """


class NE(Comparison):
    """
    Represents a logical condition that a field is not equal to a value.
    """


class GT(Comparison):
    """
    Represents a logical condition that a field is greater than a value.
    """


class GTE(Comparison):
    """
    Represents a logical condition that a field is greater than or equal to a value.
    """


class LT(Comparison):
    """
    Represents a logical condition that a field is less than a value.
    """


class LTE(Comparison):
    """
    Represents a logical condition that a field is less than or equal to a value.
    """


class CompoundOperator(Enum):
    """
    Types of compound logical operators.
    """

    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class Compound(Condition):
    """
    Represents a compound logical operator wrapping around one or more conditions.

    >>> Compound('AND', [EQ('foo', 1), EQ('bar', 2)])
    Compound('AND', [EQ('foo', 1), EQ('bar', 2)])

    >>> Compound('AND', [])
    Traceback (most recent call last):
    ValueError: Compound() requires at least one condition

    >>> Compound('OR', (EQ('foo', x) for x in range(3)))
    Compound('OR', [EQ('foo', 0), EQ('foo', 1), EQ('foo', 2)])
    """

    operator: CompoundOperator
    components: list[Condition]

    def __init__(
        self,
        operator: CompoundOperator | str,
        components: Iterable[Condition],
    ) -> None:
        if isinstance(operator, str):
            operator = CompoundOperator[operator]
        if not isinstance(components, list):
            components = list(components)
        if len(components) == 0:
            raise ValueError("Compound() requires at least one condition")

        self.operator = operator
        self.components = components

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}({self.operator.value!r}, {self.components!r})"
        )

    def __iter__(self) -> Iterator[Condition]:
        return iter(self.components)

    def flatten(self, /, memo: set | None = None) -> Compound:
        """
        Reduces the depth of nested AND, OR, and NOT statements.

        >>> a = EQ("a", "a")
        >>> b = EQ("b", "b")
        >>> c = EQ("c", "c")
        >>> d = EQ("d", "d")
        >>> e = EQ("e", "e")
        >>> c = (a & b) & (c & (d | e))
        >>> c
        Compound('AND', [Compound('AND', [EQ('a', 'a'),
                                          EQ('b', 'b')]),
                         Compound('AND', [EQ('c', 'c'),
                                          Compound('OR', [EQ('d', 'd'),
                                                          EQ('e', 'e')])])])
        >>> c.flatten()
        Compound('AND', [EQ('a', 'a'),
                         EQ('b', 'b'),
                         EQ('c', 'c'),
                         Compound('OR', [EQ('d', 'd'), EQ('e', 'e')])])
        >>> (~c).flatten()
        Compound('NOT',
            [Compound('AND', [EQ('a', 'a'),
                              EQ('b', 'b'),
                              EQ('c', 'c'),
                              Compound('OR', [EQ('d', 'd'), EQ('e', 'e')])])])

        In the event of a circular dependency, throws an exception.

        >>> circular = NOT(Expression("x"))
        >>> circular.components = [circular]
        >>> circular.flatten()
        Traceback (most recent call last):
        boolean_expression.CircularDependency: Compound('NOT', [Compound('NOT', [...])])
        """
        memo = memo if memo else set()
        memo.add(id(self))
        flattened: list[Condition] = []
        for item in self.components:
            if id(item) in memo:
                raise CircularDependency(item)
            if isinstance(item, Compound) and item.operator == self.operator:
                flattened.extend(item.flatten(memo=memo).components)
            else:
                flattened.append(item.flatten())

        return Compound(self.operator, flattened)


class CircularDependency(RecursionError):
    """
    Raised if we detect a circular dependency when flattening nested conditions.
    """


def AND(*components: Condition, **fields: Any) -> Compound:
    """
    Joins one or more logical conditions into an AND compound condition.

    >>> AND(EQ("foo", 1), EQ("bar", 2), baz=3)
    Compound('AND', [EQ('foo', 1), EQ('bar', 2), EQ('baz', 3)])
    """
    items = list(components)
    if fields:
        items.extend(EQ(k, v) for (k, v) in fields.items())
    return Compound(CompoundOperator.AND, items)


def OR(*components: Condition, **fields: Any) -> Compound:
    """
    Joins one or more logical conditions into an OR compound condition.

    >>> OR(EQ("foo", 1), EQ("bar", 2), baz=3)
    Compound('OR', [EQ('foo', 1), EQ('bar', 2), EQ('baz', 3)])
    """
    items = list(components)
    if fields:
        items.extend(EQ(k, v) for (k, v) in fields.items())
    return Compound(CompoundOperator.OR, items)


def NOT(component: Condition | None = None, /, **fields: Any) -> Compound:
    """
    Wraps one logical condition in a negation compound.

    Can be called either explicitly or with kwargs, but not both.

    >>> NOT(EQ("foo", 1))
    Compound('NOT', [EQ('foo', 1)])

    >>> NOT(foo=1)
    Compound('NOT', [EQ('foo', 1)])

    If not called with exactly one condition, will throw an exception:

    >>> NOT(EQ("foo", 1), EQ("bar", 2))
    Traceback (most recent call last):
    TypeError: NOT() takes from 0 to 1 positional arguments but 2 were given

    >>> NOT(EQ("foo", 1), bar=2)
    Traceback (most recent call last):
    ValueError: NOT() requires exactly one condition; got 2

    >>> NOT(foo=1, bar=2)
    Traceback (most recent call last):
    ValueError: NOT() requires exactly one condition; got 2

    >>> NOT()
    Traceback (most recent call last):
    ValueError: NOT() requires exactly one condition; got 0
    """
    items: list[Condition] = [EQ(k, v) for (k, v) in fields.items()]
    if component:
        items.append(component)
    if (count := len(items)) != 1:
        raise ValueError(f"NOT() requires exactly one condition; got {count}")
    return Compound(CompoundOperator.NOT, items)


FormatStringAndDelimiter = Tuple[str, str]


class Renderer:
    """
    Renders a set of logical conditions in a human-readable expression.

    >>> condition = EQ("foo", 1) & EQ("oof", 1) & NOT(OR(EQ("bar", 2), EQ("baz", 3)))
    >>> Renderer().to_str(condition)
    '(foo=1 and oof=1 and not (bar=2 or baz=3))'
    """

    # Define the format string and separator to use when rendering
    # compound conditions to strings.
    #
    # The first item in the tuple is a format string containing '{items}'.
    # The second item in the tuple is used to join each formatted condition.
    compounds: dict[CompoundOperator, FormatStringAndDelimiter] = {
        CompoundOperator.AND: ("({items})", " and "),
        CompoundOperator.OR: ("({items})", " or "),
        CompoundOperator.NOT: ("not {items}", ""),
    }

    # Maps our Comparison classes to the operator between lvar and rvar.
    comparisons: dict[type[Comparison], str] = {
        EQ: "=",
        NE: "!=",
        GT: ">",
        GTE: ">=",
        LT: "<",
        LTE: "<=",
    }

    def to_str(self, condition: Condition) -> str:
        """
        Returns a string representation of the given logical condition.

        >>> class UnsupportedType(Condition):
        ...     pass
        >>> Renderer().to_str(UnsupportedType())
        Traceback (most recent call last):
        TypeError: <class 'boolean_expression.UnsupportedType'>
        """
        if isinstance(condition, Comparison):
            return self.render_comparison(condition)

        name = f"render_{condition.__class__.__name__.lower()}"
        condition = condition.flatten()
        if renderer := getattr(self, name, None):
            return renderer(condition)

        raise TypeError(type(condition))

    def render_expression(self, expression: Expression) -> str:
        """
        Returns the given expression. Usually a no-op.
        """
        return str(expression)

    def render_compound(self, compound: Compound) -> str:
        """
        Renders a compound condition to a str using the class variable `compounds`.
        """
        fmt, joiner = self.compounds[compound.operator]
        items = joiner.join(self.to_str(item) for item in compound)
        return fmt.format(items=items)

    def render_comparison(self, comparison: Comparison) -> str:
        """
        Renders a single comparison to a str using the class variable `comparisons`.
        """
        field = self.format_field(comparison.field)
        value = self.format_value(comparison.value)
        operator = self.comparisons[type(comparison)]
        return f"{field}{operator}{value}"

    def format_field(self, field: str) -> str:
        """
        Reformats and escapes the field component of a comparison into a
        suitable domain-specific representation.
        """
        return field

    def format_value(self, value: Any) -> str:
        """
        Reformats and escapes the value component of a comparison into a
        suitable domain-specific representation.
        """
        return str(value)


class PythonRenderer(Renderer):
    """
    Renders a set of logical conditions into a Python boolean expression.

    >>> cond = EQ("foo", "FOO!") | (
    ...     GT("baz", datetime.date(2023, 1, 23))
    ...     & ~LT("woof", 0)
    ... )
    >>> PythonRenderer().to_str(cond)
    "(foo == 'FOO!' or (baz > datetime.date(2023, 1, 23) and not woof < 0))"
    """

    comparisons = {
        EQ: " == ",
        NE: " != ",
        GT: " > ",
        GTE: " >= ",
        LT: " < ",
        LTE: " <= ",
    }

    def format_value(self, value: Any) -> str:
        return repr(value)


class LdapRenderer(Renderer):
    """
    Renders a set of logical conditions representing an LDAP query.

    >>> cond = (EQ("foo", 1) | EQ("bar", datetime.date(2023, 1, 23))) & GT("baz", 3)
    >>> LdapRenderer().to_str(cond)
    '(&(|(foo=1)(bar=20230123000000Z))(baz>3))'

    >>> cond = NE("memberOf", "group") & EQ("name", None)
    >>> LdapRenderer().to_str(cond)
    '(&(!(memberOf:1.2.840.113556.1.4.1941=group))(!name=*))'
    """

    compounds = {
        CompoundOperator.AND: ("(&{items})", ""),
        CompoundOperator.OR: ("(|{items})", ""),
        CompoundOperator.NOT: ("(!{items})", ""),
    }

    def to_str(self, component: Condition) -> str:
        # LDAP does not have a != operator, so convert NE() to NOT(EQ())
        if isinstance(component, NE):
            return super().to_str(NOT(EQ(component.field, component.value)))
        return super().to_str(component)

    def render_comparison(self, comparison: Comparison) -> str:
        # null properties are not populated in LDAP, so None is a special case
        if comparison.value is None:
            return f"(!{comparison.field}=*)"
        return "(%s)" % super().render_comparison(comparison)

    def format_field(self, field: str) -> str:
        if field == "memberOf":
            return "memberOf:1.2.840.113556.1.4.1941"
        return super().format_field(field)

    def format_value(self, value: Any) -> str:
        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.strftime("%Y%m%d%H%M%SZ")
        return super().format_value(value)


class AirtableRenderer(Renderer):
    """
    Renders a set of logical conditions representing an Airtable API query.

    >>> condition1 = (
    ...     EQ("foo", 1)
    ...     | EQ("bar", datetime.date(2023, 1, 23))
    ...     | EQ("missing", None)
    ... )
    >>> AirtableRenderer().to_str(condition1)
    "OR({foo}=1, {bar}='2023-01-23', {missing}=EMPTY())"

    >>> condition2 = GTE("baz", Decimal('3.5')) & NE("quux", False)
    >>> AirtableRenderer().to_str(condition2)
    'AND({baz}>=3.5, {quux}!=0)'

    >>> condition3 = (
    ...     LT("{Date Field}", Expression("TODAY()"))
    ...     & Expression('LAST_MODIFIED_TIME() >= "2023-01-01"')
    ... )
    >>> AirtableRenderer().to_str(condition3)
    'AND({Date Field}<TODAY(), LAST_MODIFIED_TIME() >= "2023-01-01")'

    >>> condition = EQ("baz", ["lists", "not", "supported"])
    >>> AirtableRenderer().to_str(condition)
    Traceback (most recent call last):
    TypeError: <class 'list'>
    """

    compounds = {
        CompoundOperator.AND: ("AND({items})", ", "),
        CompoundOperator.OR: ("OR({items})", ", "),
        CompoundOperator.NOT: ("NOT({items})", ", "),
    }

    def format_field(self, field: str) -> str:
        if not (field.startswith("{") and field.endswith("}")):
            return "{" + field + "}"
        return field

    def format_value(self, value: Any) -> str:
        if value is None:
            return "EMPTY()"
        elif isinstance(value, bool):
            return str(int(value))
        elif isinstance(value, (datetime.date, datetime.datetime)):
            return repr(value.isoformat())
        elif isinstance(value, (int, float, Decimal, Expression)):
            return str(value)
        else:
            raise TypeError(type(value))
