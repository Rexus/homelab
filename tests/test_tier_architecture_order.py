"""Architecture readers can follow ordered, illustrated capability designs."""

import re

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class ArchitectureOrder(TierRepositoryTestCase):
    def test_each_architecture_page_has_a_figure_in_source_and_generated_manual(self):
        self.generate()
        source = UPSTREAM / "docs/01-architecture"
        generated = self.root / "verify-architecture/docs/auto-docs/01-architecture"
        for page in source.rglob("*.md"):
            relative = page.relative_to(source)
            for root in (source, generated):
                content = (root / relative).read_text(encoding="utf-8")
                self.assertRegex(content, r"```mermaid\s|!\[[^]]*\]\([^)]+\.(?:svg|png)\)",
                                 str(root / relative))

    def test_folders_and_detail_files_expose_a_foundation_first_reading_order(self):
        root = UPSTREAM / "docs/01-architecture"
        folders = sorted(path.name for path in root.iterdir() if path.is_dir())
        self.assertEqual(folders[:4], ["10-hosting", "11-networking", "12-data", "13-software-intake"])
        self.assertLess(folders.index("13-software-intake"), folders.index("18-identity"))
        self.assertTrue((root / "10-hosting/02-bootstrap.md").is_file())
        for page in root.rglob("*.md"):
            if page.name != "README.md":
                self.assertRegex(page.name, r"^\d{2}-", str(page))

    def test_proxy_sequence_distinguishes_cached_http_and_https_tunnels(self):
        page = UPSTREAM / "docs/01-architecture/13-software-intake/README.md"
        text = page.read_text(encoding="utf-8")
        self.assertIn("sequenceDiagram", text)
        self.assertIn("Fresh cache hit", text)
        self.assertIn("cacheable HTTP", text)
        self.assertIn("HTTPS CONNECT", text)
        self.assertRegex(text, r"Encrypted payload is not cached")

    def test_figures_have_explanatory_captions_in_source_and_generated_manual(self):
        self.generate()
        source = UPSTREAM / "docs/01-architecture"
        generated = self.root / "verify-architecture/docs/auto-docs/01-architecture"
        for page in source.rglob("*.md"):
            for root in (source, generated):
                current = root / page.relative_to(source)
                text = current.read_text(encoding="utf-8")
                figures = re.findall(r"```mermaid\s*\n.*?\n```\s*\n([^\n]+)", text, re.S)
                self.assertTrue(figures, str(current))
                for caption in figures:
                    self.assertTrue(caption.startswith("*Figure: "), f"{current}: {caption}")

    def test_overview_shows_capability_map_before_navigation_tables(self):
        text = (UPSTREAM / "docs/01-architecture/README.md").read_text(encoding="utf-8")
        self.assertLess(text.index("## Functional structure"), text.index("## Capabilities"))
        self.assertLess(text.index("```mermaid"), text.index("## Capabilities"))
