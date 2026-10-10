import unittest

from executor.ui.editor_logic import indentation_for_enter, lexical_spans


class EditorLogicTests(unittest.TestCase):
    def test_python_indentation_and_block_dedent(self):
        self.assertEqual(indentation_for_enter("    value = 1", "python"), "    ")
        self.assertEqual(indentation_for_enter("if ready:", "python"), "    ")
        self.assertEqual(indentation_for_enter('if item == "a:#b": # block', "python"), "    ")
        self.assertEqual(indentation_for_enter("    if ready:", "python"), "        ")
        for statement in ("return value", "raise Error()", "break", "continue", "pass"):
            self.assertEqual(indentation_for_enter("        " + statement, "python"), "    ")

    def test_non_python_indentation_only_carries_existing_indent(self):
        self.assertEqual(indentation_for_enter("if (ready) {", "javascript"), "")
        self.assertEqual(indentation_for_enter("    echo yes", "bash"), "    ")

    def test_python_highlighting_excludes_keywords_in_strings_and_comments(self):
        source = 'def run():\n    text = "return # nope" # pass\n    return 4\n'
        spans = lexical_spans(source, "python")
        keyword_text = [source[a:b] for tag, a, b in spans if tag == "keyword"]
        strings = [source[a:b] for tag, a, b in spans if tag == "string"]
        comments = [source[a:b] for tag, a, b in spans if tag == "comment"]
        self.assertEqual(keyword_text, ["def", "return"])
        self.assertEqual(strings, ['"return # nope"'])
        self.assertEqual(comments, ["# pass"])

    def test_language_lexers_respect_string_and_comment_boundaries(self):
        cases = {
            "javascript": ('const text = "return //"; // while\n', "const", "// while", "return"),
            "bash": ("if echo 'then #'; then # fi\n", "if", "# fi", "then"),
            "powershell": ('if ($true) { "return #" } <# while #>\n', "if", "<# while #>", "return"),
            "cpp": ('int main() { const char* s = "return //"; // while\n}', "int", "// while", "return"),
        }
        for language, (source, keyword, comment, string_marker) in cases.items():
            with self.subTest(language=language):
                spans = lexical_spans(source, language)
                self.assertIn(keyword, [source[a:b] for tag, a, b in spans if tag == "keyword"])
                self.assertIn(comment, [source[a:b] for tag, a, b in spans if tag == "comment"])
                string_text = [source[a:b] for tag, a, b in spans if tag == "string"]
                self.assertTrue(any(string_marker in value for value in string_text))


if __name__ == "__main__":
    unittest.main()
