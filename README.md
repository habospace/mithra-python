# mithra-python

**An interpreted language (called mithra) baby project implemented in Python to illustrate concepts such as:**
- Abstract Syntax Tree (AST) parsing with parser combinators.
- evaluation of parsed AST

**This mini project was inspired by the following blogposts and papers:**
- monadic parser combinators in haskell: https://www.cs.nott.ac.uk/~pszgmh/monparsing.pdf
- write yourself a scheme: https://en.wikibooks.org/wiki/Write_Yourself_a_Scheme_in_48_Hours

```python
@dataclass
class Text:
    chars: str
    pointer: int = 0

    def get_next(self) -> str | None:
        try:
            return self.chars[self.pointer]
        except IndexError:
            return None
        finally:
            self.pointer += 1

    def decr_pointer(self) -> None:
        if self.pointer > 0:
            self.pointer -= 1

T = TypeVar("T")


Parser: TypeAlias = Callable[[Text], T | None]


def run_parser(parser_f: Parser[T]) -> Parser[T]:
    def inner(t: Text) -> T | None:
        before_pointer = t.pointer
        if (result := parser_f(t)) is None:
            t.pointer = before_pointer
        return result

    return inner


@dataclass(frozen=True)
class Function:
    name: str
    args: tuple[str, ...]
    exprs: tuple["AstValue", ...]


@dataclass(frozen=True)
class FunctionCall:
    name: str
    arg_exprs: tuple["AstValue", ...]


@dataclass(frozen=True)
class Assignment:
    var_name: str
    expr: "AstValue"


@dataclass(frozen=True)
class Variable:
    name: str


AstValue: TypeAlias = (
      int
    | float
    | str
    | list["AstValue"]
    | Function
    | FunctionCall
    | Assignment
    | Variable
)


T1, T2 = TypeVar("T1"), TypeVar("T2")


def sep_by(main_parser: Parser[T1], sep_parser: Parser[T2]) -> Parser[list[T1]]:
    @run_parser
    def parser(t: Text) -> list[T1] | None:
        if (first := main_parser(t)) is None:
            return None
        results = [first]
        while True:
            if not sep_parser(t):
                break
            if next := main_parser(t):
                results.append(next)
        return results

    return parser

# check the script for the parser implementations...
```
