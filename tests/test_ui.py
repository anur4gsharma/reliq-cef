import os
import tkinter as tk
import unittest
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
