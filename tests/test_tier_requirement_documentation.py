"""Generated reference manuals retain downloadable evidence and inspectable CI sources."""
from pathlib import Path
from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class RequirementDocumentation(TierRepositoryTestCase):
    def test_report_assets_and_ci_links_survive_collection_generation(self):
        self.generate()
        manual = self.root / 'verify-architecture/docs/auto-docs'
        if not manual.exists():
            manual = self.parent / 'verify-architecture/docs/auto-docs'
        self.assertTrue(manual.is_dir(), str(manual))
        archive = Path('artifacts/architecture/evidence/software-intake/requirement-proof-2026-11-20.zip')
        self.assertEqual((manual / archive).read_bytes(), (UPSTREAM / archive).read_bytes())
        pipeline = manual / 'upstream/.gitlab-ci.yml'
        self.assertEqual(pipeline.read_bytes(), (UPSTREAM / '.gitlab-ci.yml').read_bytes())
        text = (manual / '04-development/requirement-reporting.md').read_text()
        self.assertIn('../upstream/.gitlab-ci.yml', text)
