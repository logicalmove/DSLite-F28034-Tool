import importlib.util
import pathlib
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_module(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DSLiteToolV2HelperTests(unittest.TestCase):
    def test_relative_ccxml_resolves_from_script_directory(self):
        module = load_module(PROJECT_ROOT / "dslite_tool_v2.py")

        resolved = module.resolve_ccxml_path("f28034.ccxml")

        self.assertEqual(resolved, str(PROJECT_ROOT / "f28034.ccxml"))

    def test_absolute_ccxml_is_preserved(self):
        module = load_module(PROJECT_ROOT / "dslite_tool_v2.py")
        absolute = str(PROJECT_ROOT / "custom.ccxml")

        self.assertEqual(module.resolve_ccxml_path(absolute), absolute)

    def test_dslite_exe_is_expanded_to_selected_tool_directory(self):
        module = load_module(PROJECT_ROOT / "dslite_tool_v2.py")
        bin_dir = str(PROJECT_ROOT / "test" / "ccs_base" / "DebugServer" / "bin")

        args = module.normalize_dslite_args(["DSLite.exe", "help"], bin_dir)

        self.assertEqual(args[0], str(pathlib.Path(bin_dir) / "DSLite.exe"))
        self.assertEqual(args[1:], ["help"])

    def test_bundled_dslite_is_detected_before_system_install(self):
        module = load_module(PROJECT_ROOT / "dslite_tool_v2.py")
        expected = str(PROJECT_ROOT / "test" / "ccs_base" / "DebugServer" / "bin")

        self.assertEqual(module.find_dslite(), expected)


if __name__ == "__main__":
    unittest.main()
