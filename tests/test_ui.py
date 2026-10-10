import os
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from executor.ui.window import ReliqWindow


class ReliqMenuCallbackTests(unittest.TestCase):
    def test_set_commands_routes_every_action_to_its_menu_item(self):
        window = ReliqWindow.__new__(ReliqWindow)
        window.file_menu = Mock()
        window.run_menu = Mock()
        calls = []
        callbacks = {
            name: (lambda name=name: calls.append(name))
            for name in ("new", "open", "save", "save_as", "run", "stop")
        }

        window.set_commands(
            new_file=callbacks["new"],
            open_file=callbacks["open"],
            save=callbacks["save"],
            save_as=callbacks["save_as"],
            run=callbacks["run"],
            stop=callbacks["stop"],
        )

        menu_calls = window.file_menu.entryconfigure.call_args_list
        for expected_index, call in enumerate(menu_calls):
            self.assertEqual(call.args[0], expected_index)
            call.kwargs["command"]()
        run_calls = window.run_menu.entryconfigure.call_args_list
        self.assertEqual([call.args[0] for call in run_calls], [0, 1])
        for call in run_calls:
            call.kwargs["command"]()
        self.assertEqual(calls, ["new", "open", "save", "save_as", "run", "stop"])

    def test_window_initializes_and_runs_menu_callbacks(self):
        try:
            import tkinter
            tkinter.Tk().destroy()
        except tk.TclError as exc:
            if os.environ.get("RELIQ_REQUIRE_GUI"):
                self.fail(f"GUI was required but Tk could not initialize: {exc}")
            self.skipTest(f"no display available: {exc}")

        view = ReliqWindow([])
        calls = []
        callbacks = [lambda name=name: calls.append(name)
                     for name in ("new", "open", "save", "save_as", "run", "stop")]
        try:
            view.set_commands(
                new_file=callbacks[0], open_file=callbacks[1], save=callbacks[2],
                save_as=callbacks[3], run=callbacks[4], stop=callbacks[5],
            )
            view.file_menu.invoke(0)
            view.file_menu.invoke(1)
            view.file_menu.invoke(2)
            view.file_menu.invoke(3)
            view.run_menu.invoke(0)
            view.run_menu.invoke(1)
            view.editor.text.insert("1.0", "print('gui-smoke')")
            self.assertEqual(view.editor.text.get("1.0", "end-1c"), "print('gui-smoke')")
            view.set_running(True, True)
            self.assertEqual(str(view.toolbar.run_button["state"]), "disabled")
            self.assertEqual(str(view.toolbar.stop_button["state"]), "normal")
            view.set_running(False, False)
            self.assertEqual(str(view.toolbar.stop_button["state"]), "disabled")
            self.assertEqual(calls, ["new", "open", "save", "save_as", "run", "stop"])
        finally:
            view.root.destroy()

    def test_editor_pairing_indentation_selection_and_undo(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            if os.environ.get("RELIQ_REQUIRE_GUI"):
                self.fail(f"GUI was required but Tk could not initialize: {exc}")
            self.skipTest(f"no display available: {exc}")
        from executor.ui.editor import CodeEditor
        editor = CodeEditor(root)
        editor.pack(fill="both", expand=True)
        root.update()
        text = editor.text
        try:
            for opener, closer in (("(", ")"), ("[", "]"), ("{", "}"), ("'", "'"), ('"', '"'), ("`", "`")):
                text.delete("1.0", "end")
                event = SimpleNamespace(keysym="parenleft", char=opener, state=0)
                self.assertEqual(editor._key_press(event), "break")
                self.assertEqual(text.get("1.0", "end-1c"), opener + closer)
                self.assertEqual(text.index("insert"), "1.1")
                self.assertTrue(editor._backspace_special())
                self.assertEqual(text.get("1.0", "end-1c"), "")

            text.insert("1.0", "abc")
            text.tag_add("sel", "1.0", "1.3")
            editor._insert_pair("(")
            self.assertEqual(text.get("1.0", "end-1c"), "(abc)")
            self.assertEqual(text.get("insert - 1c", "insert"), "c")
            text.edit_undo()
            self.assertEqual(text.get("1.0", "end-1c"), "abc")
            text.edit_redo()
            self.assertEqual(text.get("1.0", "end-1c"), "(abc)")

            text.delete("1.0", "end")
            text.insert("1.0", "()")
            text.mark_set("insert", "1.1")
            editor._key_press(SimpleNamespace(keysym="parenright", char=")", state=0))
            self.assertEqual(text.get("1.0", "end-1c"), "()")
            self.assertEqual(text.index("insert"), "1.2")

            text.delete("1.0", "end")
            editor._insert_pair("(")
            editor._newline()
            self.assertEqual(text.get("1.0", "end-1c"), "(\n    \n)")
            self.assertEqual(text.index("insert"), "2.4")

            text.delete("1.0", "end")
            text.insert("1.0", "if ready:")
            text.mark_set("insert", "end-1c")
            editor.set_language("python")
            editor._newline()
            self.assertEqual(text.get("1.0", "end-1c"), "if ready:\n    ")
            text.delete("1.0", "end")
            text.insert("1.0", "    return value")
            text.mark_set("insert", "end-1c")
            editor._newline()
            self.assertEqual(text.get("2.0", "end-1c"), "")
            self.assertEqual(text.index("insert"), "2.4")

            text.delete("1.0", "end")
            text.insert("1.0", "one\ntwo\n")
            text.tag_add("sel", "1.0", "2.3")
            editor._indent_lines()
            self.assertEqual(text.get("1.0", "end-1c"), "    one\n    two\n")
            self.assertTrue(text.tag_ranges("sel"))
            editor._dedent_lines()
            self.assertEqual(text.get("1.0", "end-1c"), "one\ntwo\n")

            text.delete("1.0", "end")
            text.insert("1.0", "value")
            text.mark_set("insert", "1.5")
            editor._indent_lines()
            self.assertEqual(text.get("1.0", "end-1c"), "    value")
            editor._dedent_lines()
            self.assertEqual(text.get("1.0", "end-1c"), "value")
        finally:
            root.destroy()

    def test_editor_quote_context_and_normal_backspace(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            if os.environ.get("RELIQ_REQUIRE_GUI"):
                self.fail(f"GUI was required but Tk could not initialize: {exc}")
            self.skipTest(f"no display available: {exc}")
        from executor.ui.editor import CodeEditor
        editor = CodeEditor(root); editor.pack(); root.update()
        text = editor.text
        try:
            text.insert("1.0", "value")
            text.mark_set("insert", "end-1c")
            self.assertIsNone(editor._key_press(SimpleNamespace(keysym="quotedbl", char='"', state=0)))
            self.assertEqual(text.get("1.0", "end-1c"), "value")
            text.delete("1.0", "end")
            text.insert("1.0", "\\")
            text.mark_set("insert", "1.1")
            self.assertIsNone(editor._key_press(SimpleNamespace(keysym="quoteright", char="'", state=0)))
            self.assertEqual(text.get("1.0", "end-1c"), "\\")
            text.insert("insert", "x")
            self.assertFalse(editor._backspace_special())
            text.delete("insert - 1c", "insert")
            self.assertEqual(text.get("1.0", "end-1c"), "value")
        finally:
            root.destroy()

    def test_runtime_refresh_preserves_selection_and_does_not_replace_missing_choice(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            if os.environ.get("RELIQ_REQUIRE_GUI"):
                self.fail(f"GUI was required but Tk could not initialize: {exc}")
            self.skipTest(f"no display available: {exc}")
        from reliq.runtime import Runtime
        from executor.ui.toolbar import Toolbar
        first = Runtime("Python", "py", "/runtime/one", "Python 3.12", "Python 3.12 · first", "project environment")
        second = Runtime("Python", "py", "/runtime/two", "Python 3.12", "Python 3.12 · second", "PATH")
        toolbar = Toolbar(root, [first, second]); toolbar.pack()
        try:
            toolbar.set_options([first, second])
            toolbar.selector.current(1)
            self.assertEqual(toolbar.selected_option().executable, "/runtime/two")
            toolbar.set_options([first, second])
            self.assertEqual(toolbar.selected_option().executable, "/runtime/two")
            toolbar.set_options([first])
            self.assertIsNone(toolbar.selected_option())
            toolbar.set_options([first])
            self.assertIsNone(toolbar.selected_option())
            self.assertIn("No usable runtime", toolbar.details.get())
            toolbar.selector.current(0)
            self.assertEqual(toolbar.selected_option().executable, "/runtime/one")
            toolbar.select_language("bash")
            self.assertIsNone(toolbar.selected_option())
            toolbar.set_options([first])
            self.assertEqual(toolbar.language_value.get(), "Bash")
            self.assertIsNone(toolbar.selected_option())
        finally:
            root.destroy()

    def test_installed_application_launch_initializes_and_returns(self):
        import reliq.app as app

        original_window = app.ReliqWindow

        class AutoCloseWindow(original_window):
            def __init__(self, options):
                super().__init__(options)
                self.root.after(250, self.root.destroy)

        try:
            tk.Tk().destroy()
        except tk.TclError as exc:
            if os.environ.get("RELIQ_REQUIRE_GUI"):
                self.fail(f"GUI was required but Tk could not initialize: {exc}")
            self.skipTest(f"no display available: {exc}")
        with patch.object(app, "ReliqWindow", AutoCloseWindow):
            self.assertEqual(app.launch(), 0)


if __name__ == "__main__":
    unittest.main()
