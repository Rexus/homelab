"""Public and generated manuals stay reachable from their repository front doors."""

from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from test_tier_deployment_navigation import links, prose
from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


def targets(document):
    content = prose(document.read_text(encoding="utf-8"))
    yield from (link.target for link in links(document))
    # Reference-style links and images are also navigation, but fenced examples are not.
    extra = re.findall(r"(?m)^\s*\[[^\]]+\]:\s*(<[^>]+>|[^\s]+)", content)
    extra += re.findall(r"!\[[^\]]*\]\(\s*(<[^>]+>|[^\s)]+)", content)
    extra += re.findall(r'<(?:a|img)\s+[^>]*(?:href|src)=[\'"]([^\'"]+)', content)
    for value in extra:
        url = urlsplit(value.strip("<>"))
        if not url.scheme and not url.netloc and url.path:
            yield (document.parent / unquote(url.path)).resolve()


def reachable(documents, frontdoors):
    pending, seen = list(frontdoors), set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        if current not in documents or current.suffix.lower() != ".md":
            continue
        for target in targets(current):
            if target.is_dir():
                target /= "README.md"
            if target in documents and target not in seen:
                pending.append(target)
    return seen


class DocumentationGraph(TierRepositoryTestCase):
    def assert_manual_reachable(self, root, frontdoors):
        documents = {path.resolve() for path in root.rglob("*.md")}
        assets = {path.resolve() for path in root.rglob("*")
                  if path.suffix.lower() in (".svg", ".png", ".mmd", ".drawio", ".puml")}
        frontdoors = {path.resolve() for path in frontdoors}
        known = documents | assets | frontdoors
        visited = reachable(known, frontdoors)
        missing = sorted(str(path.relative_to(root)) for path in known - visited)
        self.assertEqual(missing, [], "Unreachable manual pages or diagram assets")

    def test_public_manual_and_assets_are_reachable_from_upstream_readme(self):
        docs = UPSTREAM / "docs"
        self.assert_manual_reachable(docs, [UPSTREAM / "README.md"])

    def test_generated_manual_and_project_records_are_reachable_from_repo_readmes(self):
        self.generate()
        frontdoors = [self.root / f"verify-{name}/README.md"
                      for name in ("architecture", "shared", "tier-0", "tier-1", "tier-2")]
        self.assert_manual_reachable(self.root, frontdoors)

    def test_inbound_links_from_an_orphan_cycle_do_not_make_pages_discoverable(self):
        root = Path(self.temp.name) / "isolated-manual"
        root.mkdir()
        for name, text in {
            "README.md": "[Start](start.md)",
            "start.md": "# Start\n\n![Figure](pixel.png)",
            "lost.md": "[Other orphan](lost-again.md)",
            "lost-again.md": "[First orphan](lost.md)",
        }.items():
            (root / name).write_text(text, encoding="utf-8")
        (root / "pixel.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        with self.assertRaisesRegex(AssertionError, "lost-again.md"):
            self.assert_manual_reachable(root, [root / "README.md"])
