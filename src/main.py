from typing import TypeVar, Callable, TypeAlias
from dataclasses import dataclass
from collections.abc import Iterable

# Instead of just spending most of the time
# explaining my own language I thought it
# would be cooler and more useful if we
# implemented a super minimalistic language
# together. But I will show my language in
# the end and we will implement the filter
# in it as well.

# Disclaimer: the ideas I am using here are not my own
# I took a lot of inspiration on how to write parsers
# from Graham Hutton's paper on monadic parser
# combinators in haskell:
# https://www.cs.nott.ac.uk/~pszgmh/monparsing.pdf
# and from a book called write yourself a scheme
# which is in haskell again and it helped
# me write the interpreter or the evaluator part
# https://en.wikibooks.org/wiki/Write_Yourself_a_Scheme_in_48_Hours
# I put the links for both into the script if you're interested

# Parts of an interpreted language:
# 1. Lexer: raw str -> tokens
# 2. Parser: tokens -> to AST (Abstract Syntax Tree)
# 3. Interpreter: evaluates the AST

# In case of mithra (the name of the language) we just have:
# 1. Parser: str -> AST
# 2. Interpreter: evaluates AST

# How do we represent the raw text?


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

# (t: Text) -> T | None
# we use 'None' to indicate failure  for the sake of simplicity
# but when you're more serious you'd want to use something that
# can carry error context.
# would use 'Result' in Rust (I do in fact use it in the Rust version)
# or 'Either' in haskell which is essentially the inspiration for result type

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


# What is AST: some structured and managable representation
# of the expressions of my programming language that I can
# evaluate. I can't evaluate a raw string into a program
# so I have turn my raw string into something that I can
# actually handle and evaluate


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


# could be just a str but
# have to distinguish from
# primitive str so we wrap
# this into this dataclass


@dataclass(frozen=True)
class Variable:
    name: str


# 'AstValue' is the top level AST
# type that wraps around all the previous
# AST types or dataclasses.
# So 'AstValue' can be any of those
# dataclasses or some primitive types
# eg. str or int which don't need any
# dataclasses, they're good as themeselves.

# fmt: off
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
# fmt: on


@run_parser
def parse_int(t: Text) -> int | None:
    int_builder = ""
    while char := t.get_next():
        if not char.isdigit():
            t.decr_pointer()
            break
        int_builder += char
    return int(int_builder) if int_builder else None


@run_parser
def parse_string(t: Text) -> str | None:
    if t.get_next() != '"':
        return None
    string_builder = ""
    while char := t.get_next():
        if char == '"':
            break
        string_builder += char
    return string_builder


@run_parser
def word(t: Text) -> str | None:
    word_builder = ""
    while char := t.get_next():
        if not char.isalpha():
            t.decr_pointer()
            break
        word_builder += char
    return word_builder or None


def parse_variable(t: Text) -> Variable | None:
    if (var_name := word(t)) is None:
        return None
    return Variable(var_name)


@run_parser
def parse_expr(t: Text) -> AstValue | None:
    # notice how '@run_parser' decorator becomes useful here as it resets the
    # pointer over the text everytime a previous parser fails.
    for parser in [parse_int, parse_string, parse_function_call, parse_variable]:
        if result := parser(t):
            return result
    return None


# parser factory, creates new parser: iterates over
# the chars of the string and tries to match the next
# chars of our raw text to the chars of the arg string


def create_string_parser(string: str) -> Parser[str]:
    @run_parser
    def parser(t: Text) -> str | None:
        for char in string:
            if char != t.get_next():
                return None
        return string

    return parser


T1, T2 = TypeVar("T1"), TypeVar("T2")


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


@run_parser
def parse_function_call(t: Text) -> FunctionCall | None:
    if (function_name := word(t)) is None:
        return None
    if t.get_next() != "(":
        return None
    comma_parser: Parser = create_string_parser(", ")
    # notice how expression parsing becomes recursive at this point because
    # 'parse_function_call' parses call arg expressions via 'parse_expr'
    # but 'parse_expr' then calls 'parse_function_call'. This recursivity is
    # what enables us to parse nested function calls with arbitrary levels of
    # nesting
    call_arg_parser: Parser = sep_by(main_parser=parse_expr, sep_parser=comma_parser)
    if (call_args := call_arg_parser(t)) is None:
        return None
    if t.get_next() != ")":
        return None
    return FunctionCall(function_name, tuple(call_args))


@run_parser
def parse_list(t: Text) -> list[AstValue] | None:
    # TODO: implement list parser for homework
    ...


@run_parser
def parse_assignment(t: Text) -> Assignment | None:
    if (var_name := word(t)) is None:
        return None
    assignment_parser: Parser = create_string_parser(" = ")
    if assignment_parser(t) is None:
        return None
    if (expr := parse_expr(t)) is None:
        return None
    return Assignment(var_name, expr)


# So let's imagine that our programming language
# consists of a series of single line assignment
# expressions like the on below.
code = """x = 5
y = add(mul(x, 2), add(1, sub(3, 4)))
z = div(y, 5)
"""
# x = 5
# y = (5 * 2) + (1 + (3 - 4)) or 10
# z = 10 / 5 or 2

# The above code should turn into the following AST:
exprs: list[Assignment | None] = [
    parse_assignment(Text(line)) for line in code.splitlines()
]
assert exprs == [
    # first assignment: x = 5
    Assignment(var_name="x", expr=5),
    # second very nested assignment: y = add(mul(x, 2), add(1, sub(3, 4)))
    Assignment(
        var_name="y",
        expr=FunctionCall(
            name="add",
            arg_exprs=(
                FunctionCall(name="mul", arg_exprs=(Variable(name="x"), 2)),
                FunctionCall(
                    name="add",
                    arg_exprs=(1, FunctionCall(name="sub", arg_exprs=(3, 4))),
                ),
            ),
        ),
    ),
    # z = div(y, 5)
    Assignment(
        var_name="z", expr=FunctionCall(name="div", arg_exprs=(Variable(name="y"), 5))
    ),
]


VarName: TypeAlias = str
FunctionName: TypeAlias = str
Number: TypeAlias = int | float
NumBinOpFunction: TypeAlias = Callable[[Number, Number], Number]


class Interpreter:
    memory: dict[VarName, AstValue] = {}
    default_functions: dict[FunctionName, NumBinOpFunction] = {
        "add": lambda x, y: x + y,
        "sub": lambda x, y: x - y,
        "mul": lambda x, y: x * y,
        "div": lambda x, y: x / y,
    }

    def run(self, exprs: Iterable[AstValue]) -> AstValue | None:
        # just evaluate code expression by expression
        evaluated: AstValue | None = None
        for expr in exprs:
            evaluated = self.eval(expr)
        # return final expression
        return evaluated

    # 'eval' is just trying to evaluate higher level
    # forms of AST to the most primitive or bottom level
    # form, so in case of a function call which is a high
    # level form of AST it would try to evaluate the function
    # into its most primitive return value. in case of 'add'
    # this would be an int
    def eval(self, expr: AstValue) -> AstValue:
        # when MithraVal is bottom level primitive val eg.:
        # str or int then we just return it because it's
        # already avaluated to the most pimitive level
        if isinstance(expr, (int, str)):
            return expr
        elif isinstance(assignment := expr, Assignment):
            evaluated_expr = self.eval(assignment.expr)
            self.memory[assignment.var_name] = evaluated_expr
            return evaluated_expr
        elif isinstance(var := expr, Variable):
            return self.memory[var.name]
        elif isinstance(f_call := expr, FunctionCall):
            # notice how evaluation becomes recursive here
            # because we have to evaluate each of the call
            # argument expressions which themeselves can be
            # function calls so it becomes recursive
            # fmt: off
            evaluated_args: list[Number] = [
                self.eval(arg) for arg in f_call.arg_exprs
            ]  # pyright: ignore[reportAssignmentType]
            # fmt: on
            function = self.default_functions[f_call.name]
            return function(*evaluated_args)

        raise NotImplementedError


intepreter = Interpreter()
intepreter.run((expr for expr in exprs if expr is not None))
print(intepreter.memory)
