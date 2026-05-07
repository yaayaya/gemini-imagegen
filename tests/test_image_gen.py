import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "image_gen.py"


def load_module():
    spec = importlib.util.spec_from_file_location("image_gen_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GeminiImageGenCliTests(unittest.TestCase):
    def run_main(self, argv, env=None):
        module = load_module()
        stdout = io.StringIO()
        stderr = io.StringIO()
        env_patch = {
            "GEMINI_API_KEY": "",
            "GOOGLE_API_KEY": "",
        }
        if env:
            env_patch.update(env)
        with mock.patch.object(sys, "argv", [str(SCRIPT), *argv]):
            with mock.patch.dict(os.environ, env_patch, clear=False):
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    code = module.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def test_generate_dry_run_prints_gemini_payload(self):
        code, stdout, stderr = self.run_main(
            [
                "generate",
                "--prompt",
                "Create a small ceramic mug",
                "--aspect-ratio",
                "16:9",
                "--image-size",
                "2K",
                "--out",
                "output/imagegen/mug.png",
                "--dry-run",
            ]
        )

        self.assertEqual(code, 0, stderr)
        payload = json.loads(stdout)
        self.assertEqual(payload["endpoint"], "models/gemini-3.1-flash-image-preview:generateContent")
        self.assertEqual(payload["model"], "gemini-3.1-flash-image-preview")
        self.assertEqual(payload["outputs"], ["output\\imagegen\\mug.png"])
        self.assertEqual(payload["generationConfig"]["responseModalities"], ["TEXT", "IMAGE"])
        self.assertEqual(
            payload["generationConfig"]["imageConfig"],
            {"aspectRatio": "16:9", "imageSize": "2K"},
        )
        self.assertEqual(
            payload["contents"][0]["parts"][0]["text"],
            "Primary request: Create a small ceramic mug",
        )

    def test_live_generate_requires_gemini_api_key(self):
        module = load_module()
        stderr = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            [
                str(SCRIPT),
                "generate",
                "--prompt",
                "Test",
                "--out",
                "output/imagegen/test.png",
            ],
        ):
            with mock.patch.dict(
                os.environ,
                {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""},
                clear=False,
            ):
                with mock.patch.object(module, "_load_env_file_if_present", return_value=None):
                    with contextlib.redirect_stderr(stderr):
                        with self.assertRaises(SystemExit):
                            module.main()
        self.assertIn("GEMINI_API_KEY or GOOGLE_API_KEY", stderr.getvalue())

    def test_edit_dry_run_includes_input_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "input.png"
            image_path.write_bytes(b"fake-png")
            code, stdout, stderr = self.run_main(
                [
                    "edit",
                    "--image",
                    str(image_path),
                    "--prompt",
                    "Change only the background",
                    "--aspect-ratio",
                    "1:1",
                    "--out",
                    "output/imagegen/edit.png",
                    "--dry-run",
                ]
            )

        self.assertEqual(code, 0, stderr)
        payload = json.loads(stdout)
        self.assertEqual(payload["endpoint"], "models/gemini-3.1-flash-image-preview:generateContent")
        self.assertEqual(payload["inputs"], [str(image_path)])
        self.assertEqual(payload["generationConfig"]["imageConfig"], {"aspectRatio": "1:1"})

    def test_generate_dry_run_accepts_reference_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "style.png"
            image_path.write_bytes(b"fake-png")
            code, stdout, stderr = self.run_main(
                [
                    "generate",
                    "--reference-image",
                    str(image_path),
                    "--prompt",
                    "Create a new poster using the reference image only for style",
                    "--out",
                    "output/imagegen/reference-poster.png",
                    "--dry-run",
                ]
            )

        self.assertEqual(code, 0, stderr)
        payload = json.loads(stdout)
        self.assertEqual(payload["inputs"], [str(image_path)])
        self.assertEqual(payload["inputRole"], "reference")
        self.assertEqual(payload["contents"][0]["parts"][1]["inlineData"]["mimeType"], "image/png")

    def test_loads_raw_api_key_from_env_txt(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, ".env.txt").write_text("raw-secret-key\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}, clear=False):
                with mock.patch.object(Path, "cwd", return_value=Path(tmp)):
                    module._load_env_file_if_present()
                self.assertEqual(os.environ["GEMINI_API_KEY"], "raw-secret-key")

    def test_project_text_has_no_previous_provider_terms(self):
        banned = ["open" + "ai", "g" + "pt", "g" + "pt-image", "open" + "ai_api_key"]
        ignored_dirs = {".git", "output", "tmp", "__pycache__"}
        ignored_files = {".env.txt"}
        text_suffixes = {".md", ".py", ".yaml", ".yml", ".txt", ".gitignore"}
        hits = []

        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if path.name in ignored_files:
                continue
            if any(part in ignored_dirs for part in path.parts):
                continue
            if path.suffix.lower() not in text_suffixes and path.name != ".gitignore":
                continue
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for term in banned:
                if term in text:
                    hits.append(f"{path.relative_to(ROOT)} contains {term}")

        self.assertEqual(hits, [])

    def test_setup_reference_is_generic(self):
        self.assertFalse((ROOT / "references" / "codex-network.md").exists())
        self.assertTrue((ROOT / "references" / "setup.md").exists())

    def test_skill_name_matches_project(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        agent = (ROOT / "agents" / "gemini.yaml").read_text(encoding="utf-8")
        self.assertIn('name: "gemini-imagegen"', skill)
        self.assertIn('display_name: "Gemini ImageGen"', agent)
        self.assertIn("$gemini-imagegen", agent)
        self.assertNotIn('name: "imagegen"', skill)
        self.assertNotIn("$imagegen", agent)

    def test_transparent_background_workflow_is_not_advertised(self):
        self.assertFalse((ROOT / "scripts" / "remove_chroma_key.py").exists())
        banned = ["chroma", "cutout", "remove_chroma", "background-extraction", "transparent-background cutouts"]
        checked = [
            ROOT / "README.md",
            ROOT / "README.en.md",
            ROOT / "SKILL.md",
            ROOT / "references" / "cli.md",
            ROOT / "references" / "prompting.md",
            ROOT / "references" / "sample-prompts.md",
        ]
        hits = []
        for path in checked:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for term in banned:
                if term in text:
                    hits.append(f"{path.relative_to(ROOT)} contains {term}")
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
