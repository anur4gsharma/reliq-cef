"""Small source transformations used by the Tk editor and pure unit tests."""
from __future__ import annotations

import keyword
import re
import tokenize
from io import StringIO

INDENT = "    "
PAIRS = {"(": ")", "[": "]", "{": "}"}
QUOTES = {"'": "'", '"': '"', "`": "`"}


def indentation_for_enter(line: str, language: str) -> str:
    """Return conservative indentation for a newline after ``line``."""
    base = re.match(r"[ \t]*", line).group(0).replace("\t", INDENT)
    if language.lower() != "python":
        return base
    stripped = line.strip()
    if re.match(r"(?:return|raise|break|continue|pass)\b", stripped) and len(base) >= len(INDENT):
        base = base[:-len(INDENT)]
    try:
        significant = [token for token in tokenize.generate_tokens(StringIO(line + "\n").readline)
                       if token.type not in {tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER,
                                             tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT}]
        block_colon = bool(significant and significant[-1].type == tokenize.OP and significant[-1].string == ":")
    except (tokenize.TokenError, IndentationError, SyntaxError):
        block_colon = line.rstrip().endswith(":")
    if block_colon:
        base += INDENT
    return base


def lexical_spans(source: str, language: str) -> list[tuple[str, int, int]]:
    """Return (tag, start offset, end offset) lexical spans for supported modes."""
    language = language.lower()
    if language == "python":
        return _python_spans(source)
    definitions = {
        "javascript": ("//", ("/*", "*/"), {"'", '"', "`"},
                       "break case catch class const continue debugger default delete do else export extends finally for function if import in instanceof let new return super switch this throw try typeof var void while with yield async await enum implements interface package private protected public static null true false undefined of"),
        "bash": ("#", None, {"'", '"', "`"},
                 "if then else elif fi case esac for while until do done function in select time coproc local export readonly declare return break continue exit set unset shift trap eval source test true false"),
        "powershell": ("#", ("<#", "#>"), {"'", '"'},
                       "begin break catch class continue data define do dynamicparam else elseif end exit filter finally for foreach from function if in param process return switch throw trap try until using var while workflow parallel sequence"),
        "cpp": ("//", ("/*", "*/"), {"'", '"'},
                "alignas alignof and asm auto bool break case catch char class const constexpr continue default delete do double else enum explicit export extern false float for friend if inline int long namespace new nullptr operator private protected public register reinterpret_cast return short signed sizeof static struct switch template this throw true try typedef typename union unsigned using virtual void volatile while include define ifdef ifndef endif"),
    }
    if language not in definitions:
        return _python_spans(source)
    line_comment, block_comment, quotes, words = definitions[language]
    keywords = set(words.split())
    spans = []
    i, size = 0, len(source)
    while i < size:
        if source.startswith(line_comment, i):
            end = source.find("\n", i)
            if end < 0: end = size
            spans.append(("comment", i, end)); i = end; continue
        if block_comment and source.startswith(block_comment[0], i):
            end = source.find(block_comment[1], i + len(block_comment[0]))
            end = size if end < 0 else end + len(block_comment[1])
            spans.append(("comment", i, end)); i = end; continue
        if source[i] in quotes:
            quote = source[i]
            # Bash single quotes do not interpret backslash; other strings do.
            j = i + 1
            while j < size:
                if quote != "'" and source[j] == "\\": j += 2; continue
                if source[j] == quote:
                    j += 1; break
                j += 1
            spans.append(("string", i, min(j, size))); i = min(j, size); continue
        number = re.match(r"(?:0[xX][0-9a-fA-F]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", source[i:])
        if number:
            spans.append(("number", i, i + len(number.group(0)))); i += len(number.group(0)); continue
        identifier = re.match(r"[A-Za-z_$][\w$]*", source[i:])
        if identifier:
            word = identifier.group(0)
            if word in keywords: spans.append(("keyword", i, i + len(word)))
            i += len(word); continue
        i += 1
    return spans


def _python_spans(source: str) -> list[tuple[str, int, int]]:
    offsets = [0]
    python_keywords = set(keyword.kwlist) | set(getattr(keyword, "softkwlist", ()))
    for line in source.splitlines(keepends=True): offsets.append(offsets[-1] + len(line))
    spans = []
    try:
        for token in tokenize.generate_tokens(StringIO(source).readline):
            tag = {tokenize.NAME: "keyword" if token.string in python_keywords else None,
                   tokenize.STRING: "string", tokenize.COMMENT: "comment", tokenize.NUMBER: "number"}.get(token.type)
            if tag:
                start = offsets[token.start[0] - 1] + token.start[1]
                end = offsets[token.end[0] - 1] + token.end[1]
                spans.append((tag, start, end))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # tokenize yields valid prefix tokens before incomplete input; keep them.
        pass
    return spans
