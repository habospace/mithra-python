# mithra-python

**An interpreted language (called mithra) baby project implemented in Python to illustrate language implementation concepts such as:**
- Abstract Syntax Tree (AST) parsing with parser combinators
- evaluation of parsed AST

**This mini project was inspired by the following blogposts and papers:**
- monadic parser combinators in haskell: https://www.cs.nott.ac.uk/~pszgmh/monparsing.pdf
- write yourself a scheme: https://en.wikibooks.org/wiki/Write_Yourself_a_Scheme_in_48_Hours

**Here's a bit from the source code, but please check `src/main.py` if you're interested.**

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


if TYPE CHECKING:
    T = TypeVar("T")
    Parser: TypeAlias = Callable[[Text], T | None]


# Important: we might want to try a different parser for the same
# string and we don't want to partially consume the string on a
# failed attempt, so always reset the  pointer over text when we fail.
# the 'run_parser' decorater ensures this

def run_parser(parser_f: Parser[T]) -> Parser[T]:
    def inner(t: Text) -> T | None:
        before_pointer = t.pointer
        if (result := parser_f(t)) is None:
            t.pointer = before_pointer
        return result

    return inner


# Sometimes we're overconsuming the text in which case we have
# to step back (or decr the pointer) after succession.
# for instance when we parse a number we have to step outside
# of the number to identify its final digit.
# "1234 " -> in this instance we have to consume the " " after "4"
# to know that the number's last digit is 4.

def step_back(parser_f: Parser[T]) -> Parser[T]:
    def inner(t: Text) -> T | None:
        if (result := parser_f(t)) is not None:
            t.decr_pointer()
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


if TYPE_CHECKING:
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


# A parser:

@run_parser
@step_back
def parse_int(t: Text) -> int | None:
    int_builder = ""
    while char := t.get_next():
        if not char.isdigit():
            break
        int_builder += char
    return int(int_builder) if int_builder else None


# parser combinators: create new parsers from other parsers. 'sep_by' takes a
# a separator parser and a main parser and tries to match the main parser and
# the separator parser in between as many times as it can. Very useful for parsing
# lists which are just comma separated expressions or a function call which is
# again just comma separated expressions between parentheses.
# notice that the main parser returns 'T1' but the contructed parser
# returns 'list[T1]' because it matches the main parser as many times as it can.

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

# check the script for rest implementation...
```
