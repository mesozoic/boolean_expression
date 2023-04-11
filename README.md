# boolean_expression

This is a simple library for creating nested boolean expressions and rendering them in a variety of dialects. It is provided as a single file so that it can be vendored into other projects where an external dependency is not possible or desirable. It is not assumed to be universally useful, but might be handy to someone out there.

## Getting started

You can use this library out-of-the-box as a miniature DSL to construct boolean expressions in your library, which can later be converted to a search expression, query language, or the like. For example:

```python
from boolean_expression import AND, OR, EQ, NOT

condition = AND(
    EQ("id", record_id),
    OR(
        NOT(EQ("status", "private")),
        EQ("status", "private") & EQ("owner", searching_user),
    )
)
```

There are a few built-in renderers, like one that creates LDAP expressions. Given the above, the following code...

```python
from boolean_expression import LdapRenderer
print(LdapRenderer().to_str(condition))
```

...produces the following output:

```
(&(id=theRecordId)(|(!(status=private))(&(status=private)(owner=theUser))))
```

In most cases, however, it is likely that if you're using this library you have your own particular needs and will need to implement your own renderer.

## Usage

Developers considering this library are encouraged to read the docstring tests, because they demonstrate 100% of the functionality of the library. Basics are reproduced below.

### Equality

Comparisons express an lval and an rval which are not interpreted at all during construction (but which you could choose to interpret during rendering, if appropriate to your use case).

To specify a comparison where some name or expression is expected to match a value:

```python
EQ("some_name", expected_value)
```

### Less Than / Greater Than

There are convenience methods for these common types of comparisons:

```python
LT("some_name", 0)
GT("some_name", 0)
LTE("some_name", 0)
GTE("some_name", 0)
```

### And / Or

These can be constructed in one of a few ways. The most straightforward is the "Excel style":

```python
AND(
    GT("total", 0),
    OR(
        EQ("alpha", "A"),
        EQ("bravo", "B")
    )
)
```

...which can be made more tersely by using `&` and `|` operators:

```python
GT("total", 0) & (EQ("alpha", "A") | EQ("bravo", "B"))
```

The `AND()` and `OR()` functions also accept keyword arguments (which are all interpreted as `EQ`):

```python
GT("total", 0) & OR(alpha="A", bravo="B")
```

### Negation

There are two ways of negating an expression. One is an atomic comparison, equivalent to `X != Y`:

```python
NE("some_name", "some_value")
```

The other way to construct "not equal" is with a compound condition. The following Python expressions all produce the same data structure:

```python
~EQ("some_name", "some_value")
NOT(EQ("some_name", "some_value"))
Compound("NOT", [EQ("some_name", "some_value")])
```

### Raw Expressions

Should your use case require it, the library also allows for inserting raw expressions into the data structure:

```python
AND(
    NOT(OR(Role="Admin", Role="Owner")),
    Expression("AttemptedDelete")
)
```
