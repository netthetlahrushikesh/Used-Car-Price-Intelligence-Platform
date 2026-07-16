"""Focused checks for the Vercel deployment surface (no cloud calls)."""

from __future__ import annotations

import ast
import json
import re
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class VercelDeploymentConfigTests(unittest.TestCase):
    def test_root_entrypoint_exports_app_without_local_logic(self) -> None:
        entrypoint = ROOT / "app.py"
        self.assertTrue(entrypoint.is_file(), "root app.py entrypoint is required for Vercel")

        source = entrypoint.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(entrypoint))
        imports = [
            node
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        from_imports = [
            node
            for node in imports
            if isinstance(node, ast.ImportFrom) and node.module
        ]
        reexport = [
            node
            for node in from_imports
            if node.module == "used_car_price_intelligence.api.app"
            and any(alias.name == "app" for alias in node.names)
        ]
        self.assertTrue(reexport, "entrypoint must import app from the existing package module")

        # Guard against copying route definitions into the Vercel shim.
        self.assertNotIn("FastAPI(", source)
        self.assertNotIn("@app.", source)

    def test_root_entrypoint_importable_and_is_fastapi_app(self) -> None:
        from fastapi import FastAPI

        import app as vercel_entrypoint

        self.assertIsInstance(vercel_entrypoint.app, FastAPI)
        self.assertEqual(vercel_entrypoint.app.title, "Used Car Price Intelligence API")

        paths = {getattr(route, "path", None) for route in vercel_entrypoint.app.routes}
        for required in ("/", "/health", "/model/metadata", "/predict", "/docs", "/static"):
            self.assertTrue(
                any(path == required or (path or "").startswith(required) for path in paths),
                f"missing route surface for {required}; found {sorted(p for p in paths if p)}",
            )

    def test_requirements_are_production_scoped_and_pin_sklearn(self) -> None:
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
        self.assertIn("fastapi", requirements)
        self.assertIn("scikit-learn==1.8.0", requirements)
        self.assertIn("joblib", requirements)
        self.assertIn("pandas", requirements)
        self.assertIn("numpy", requirements)

        # Notebook / acquisition-only packages must stay out of the Vercel install set.
        for blocked in ("matplotlib", "seaborn", "playwright", "pytest", "jupytext"):
            self.assertNotRegex(
                requirements,
                rf"(?m)^\s*{re.escape(blocked)}\b",
                f"{blocked} should not be a production Vercel dependency",
            )

    def test_pyproject_base_dependencies_cover_vercel_runtime(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        dependencies = [item.lower() for item in project["project"]["dependencies"]]
        for required in ("fastapi", "pydantic", "joblib", "numpy", "pandas"):
            self.assertTrue(
                any(item.startswith(required) for item in dependencies),
                f"{required} must be a base dependency because Vercel installs pyproject.toml",
            )
        self.assertIn("scikit-learn==1.8.0", dependencies)

    def test_vercel_uses_fastapi_framework_without_function_override(self) -> None:
        # Vercel discovers the root app.py FastAPI export. A functions.app.py
        # override is invalid because function patterns are limited to api/.
        config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
        self.assertEqual(config.get("framework"), "fastapi")
        self.assertNotIn("functions", config)

    def test_gitignore_can_reinclude_production_model(self) -> None:
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("artifacts/*", gitignore)
        self.assertNotRegex(gitignore, r"(?m)^artifacts/$")
        self.assertIn("!artifacts/model/", gitignore)
        self.assertIn("!artifacts/model/final_price_model_v1/**", gitignore)
        self.assertIn("!artifacts/model/final_price_model_v1/*.joblib", gitignore)

    def test_vercelignore_keeps_model_and_drops_bulk_data(self) -> None:
        ignore_path = ROOT / ".vercelignore"
        self.assertTrue(ignore_path.is_file())
        text = ignore_path.read_text(encoding="utf-8")

        for required in (
            "data/",
            "notebooks/",
            "tests/",
            "kaggle_upload/",
            "memory/",
        ):
            self.assertIn(required, text)

        # Must not ignore the whole source tree or the entrypoint.
        self.assertNotRegex(text, r"(?m)^\s*src/\s*$")
        self.assertNotRegex(text, r"(?m)^\s*app\.py\s*$")
        self.assertNotRegex(text, r"(?m)^\s*artifacts(?:/\*|/model(?:/\*)?)/?\s*$")

    def test_model_package_present_for_runtime_bundle(self) -> None:
        model_dir = ROOT / "artifacts" / "model" / "final_price_model_v1"
        joblib_path = model_dir / "final_price_model_v1.joblib"
        self.assertTrue(model_dir.is_dir(), "model package directory must exist for deploy")
        self.assertTrue(joblib_path.is_file(), "joblib artifact must exist for deploy")
        self.assertGreater(joblib_path.stat().st_size, 1_000_000)
        self.assertTrue((model_dir / "metadata.json").is_file())
        self.assertTrue((model_dir / "sample_request.json").is_file())


if __name__ == "__main__":
    unittest.main()
