"""Deployment choices remain discoverable from each capability's numbered entry point."""

from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata
from urllib.parse import unquote, urlsplit

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


def prose(text):
    """Exclude examples/diagrams without changing offsets used to locate navigation."""
    return re.sub(r"(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$",
                  lambda match: re.sub(r"[^\n]", " ", match[0]), text)


@dataclass(frozen=True)
class Link:
    target: Path
    fragment: str
    offset: int


def links(document, text=None):
    content = prose(document.read_text(encoding="utf-8") if text is None else text)
    for match in re.finditer(r"(?<!!)\[[^\]\n]+\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)", content):
        url = urlsplit(match[1].strip("<>"))
        if url.scheme or url.netloc:
            continue
        path = unquote(url.path)
        yield Link((document.parent / path).resolve() if path else document.resolve(),
                   unquote(url.fragment), match.start())


def heading_anchor(title):
    title = re.sub(r"<[^>]*>", "", title).strip().lower()
    title = "".join(char for char in title if char in " -_" or
                    unicodedata.category(char)[0] in "LN")
    return title.replace(" ", "-")


def anchors(text):
    content = prose(text)
    result = dict((match[1], match.start()) for match in
                  re.finditer(r'<a\s+(?:id|name)=[\'"]([^\'"]+)[\'"][^>]*>', content))
    counts = {}
    for match in re.finditer(r"(?m)^#{1,6}\s+(.+?)\s*#*\s*$", content):
        base = heading_anchor(match[1])
        count = counts.get(base, 0)
        counts[base] = count + 1
        result[base if count == 0 else f"{base}-{count}"] = match.start()
    return result


def steps(text):
    content = prose(text)
    headings = list(re.finditer(r"(?m)^##\s+(.+)$", content))
    starts = []
    for heading in headings:
        alias = re.search(r'(?:<a\s+(?:id|name)=[\'"][^\'"]+[\'"][^>]*>\s*</a>\s*)+$',
                          content[:heading.start()])
        starts.append(alias.start() if alias else heading.start())
    result = []
    for index, heading in enumerate(headings):
        number = re.match(r"Step\s+(\d+)(?:[a-z])?\b", heading[1], re.IGNORECASE)
        if number:
            end = starts[index + 1] if index + 1 < len(headings) else len(content)
            result.append((int(number[1]), starts[index], end))
    return result


def step_at(text, offset):
    return next((number for number, start, end in steps(text) if start <= offset < end), None)


def indexed_guides(root):
    """Only README indexes may expand a route; a leaf guide cannot hide another choice."""
    visited, discovered, pending = set(), {root.resolve()}, [root.resolve()]
    while pending:
        index = pending.pop()
        if index in visited:
            continue
        visited.add(index)
        for link in links(index):
            target = link.target
            if not target.is_relative_to(root.parent.resolve()) or target.suffix.lower() != ".md":
                continue
            discovered.add(target)
            if target.name.lower() == "readme.md" and target.is_file():
                pending.append(target)
    return discovered


def routed_from(root, option, number):
    content = root.read_text(encoding="utf-8")
    for link in links(root, content):
        if link.target != option.resolve():
            continue
        if step_at(content, link.offset) == number:
            return True
        # A numbered routing table may live above the step bodies, but an unnumbered
        # "related guides" list is not a decision point.
        line = content[content.rfind("\n", 0, link.offset) + 1:content.find("\n", link.offset)]
        if re.match(rf"\|\s*(?:Step\s+)?{number}[a-z]?\b[^|]*\|", line, re.IGNORECASE):
            return True
    return False


def field_links(document, label):
    content = prose(document.read_text(encoding="utf-8"))
    start = rf"\*\*{label}" if label != "Return" else r"(?:\*\*)?Return\b"
    for match in re.finditer(rf"(?im)^[ \t]*(?:\d+[.)]\s+|[-*]\s+)?{start}[^\n]*"
                             r"(?:\n(?!\s*\n|\*\*)[^\n]*)*", content):
        yield from links(document, match[0])


class DeploymentNavigation(TierRepositoryTestCase):
    def deployment_roots(self):
        self.generate()
        return (UPSTREAM / "docs/deployment",
                self.root / "verify-architecture/docs/auto-docs/deployment")

    def owners(self, deployment):
        stages = sorted(deployment.glob("stage-*/README.md"),
                        key=lambda path: int(path.parent.name.split("-")[1]))
        self.assertEqual([int(path.parent.name.split("-")[1]) for path in stages], list(range(1, 11)))
        return [deployment / "foundation/README.md", *stages]

    def test_every_guide_is_reachable_through_owning_readme_indexes(self):
        for deployment in self.deployment_roots():
            for root in self.owners(deployment):
                with self.subTest(tree=str(deployment), owner=root.parent.name):
                    expected = {path.resolve() for path in root.parent.rglob("*.md")}
                    missing = expected - indexed_guides(root)
                    self.assertFalse(missing, "Missing README navigation: " + ", ".join(
                        sorted(str(path.relative_to(deployment)) for path in missing)))
                    stale = []
                    for guide in expected:
                        for link in links(guide):
                            if (link.target.is_relative_to(deployment.resolve()) and
                                    link.target.suffix == ".md" and not link.target.is_file()):
                                stale.append(f"{guide.relative_to(deployment)} -> "
                                             f"{link.target.relative_to(deployment)}")
                    self.assertFalse(stale, "Stale deployment routes: " + "; ".join(stale))

    def test_leaf_links_cannot_disguise_a_missing_readme_choice(self):
        folder = self.parent / "navigation-fixture"
        (folder / "nested").mkdir(parents=True)
        root = folder / "README.md"
        root.write_text("[Guide](guide.md)\n[Index](nested/README.md)\n", encoding="utf-8")
        (folder / "guide.md").write_text("[Hidden choice](hidden.md)\n", encoding="utf-8")
        (folder / "hidden.md").write_text("# Hidden\n", encoding="utf-8")
        (folder / "nested/README.md").write_text("[Indexed](option.md)\n", encoding="utf-8")
        (folder / "nested/option.md").write_text("# Option\n", encoding="utf-8")
        reached = indexed_guides(root)
        self.assertIn((folder / "nested/option.md").resolve(), reached)
        self.assertNotIn((folder / "hidden.md").resolve(), reached)

    def test_related_links_need_the_right_step_or_an_explicit_routing_table(self):
        folder = self.parent / "routing-fixture"
        folder.mkdir(parents=True)
        root, option = folder / "README.md", folder / "step-1b-option.md"
        option.write_text("# Option\n", encoding="utf-8")
        root.write_text("## Step 1: Prepare\n\n## Step 2: Deploy\n\n"
                        "[Option](step-1b-option.md)\n", encoding="utf-8")
        self.assertFalse(routed_from(root, option, 1))
        root.write_text("## Related guides\n\n[Option](step-1b-option.md)\n\n"
                        "## Step 1: Prepare\n", encoding="utf-8")
        self.assertFalse(routed_from(root, option, 1))
        root.write_text("## Choices\n\n| Step | Route |\n| --- | --- |\n"
                        "| 1b | [Option](step-1b-option.md) |\n\n"
                        "## Step 1: Prepare\n", encoding="utf-8")
        self.assertTrue(routed_from(root, option, 1))

    def test_dedicated_path_titles_match_the_numbered_filename(self):
        for deployment in self.deployment_roots():
            for root in self.owners(deployment):
                for guide in root.parent.rglob("*.md"):
                    title = guide.read_text(encoding="utf-8").splitlines()[0]
                    route = re.match(r"# Step (\d+[a-z]?):", title)
                    if route:
                        with self.subTest(tree=str(deployment), guide=str(guide.relative_to(deployment))):
                            self.assertTrue(guide.name.startswith(f"step-{route[1]}-"),
                                            "Dedicated path filename must match its title/README route")
                            self.assertTrue(routed_from(root, guide, int(re.match(r"\d+", route[1])[0])))

    def test_numbered_files_start_at_their_owner_and_return(self):
        for deployment in self.deployment_roots():
            for root in self.owners(deployment):
                content = root.read_text(encoding="utf-8")
                root_anchors = anchors(content)
                for option in root.parent.rglob("step-*.md"):
                    with self.subTest(tree=str(deployment), option=str(option.relative_to(deployment))):
                        route = re.match(r"step-(\d+)([a-z]?)-", option.name)
                        self.assertIsNotNone(route, "Numbered files need a step or lettered option prefix")
                        number = int(route[1])
                        field = "Branch from" if route[2] else "Continue from"
                        branches = [link for link in field_links(option, field)
                                    if link.target == root.resolve() and link.fragment in root_anchors]
                        self.assertTrue(branches, f"{field} must link to a numbered owning README step")
                        for link in branches:
                            self.assertEqual(step_at(content, root_anchors[link.fragment]), number,
                                             f"{option.name} branches from the wrong step")
                        returns = [link for link in field_links(option, "Return")
                                   if link.target == root.resolve() and link.fragment in root_anchors]
                        self.assertTrue(returns, "Return must link to an existing owning README anchor")
                        self.assertTrue(routed_from(root, option, number),
                                        "Owner must offer the option under its step or numbered routing table")

    def test_stage_root_files_are_numbered_paths_not_procedures_or_references(self):
        for deployment in self.deployment_roots():
            for root in self.owners(deployment):
                for guide in root.parent.glob("*.md"):
                    if guide.name == "README.md":
                        continue
                    self.assertRegex(guide.name, r"^step-\d+[a-z]?-.+\.md$", str(guide))
            intake = deployment / "stage-1-software-intake"
            self.assertTrue((intake / "step-6-bootstrap-consumer.md").is_file())
            self.assertFalse((intake / "proxy-cache.md").exists())
            reference = deployment.parent / "reference/proxy-cache.md"
            self.assertTrue(reference.is_file())
            self.assertNotIn("```bash", reference.read_text(encoding="utf-8"))
            self.assertTrue((deployment / "stage-8-observability/step-3-infrastructure-monitoring.md").is_file())

    def test_numbered_paths_and_foundation_legacy_anchors_keep_the_reader_order(self):
        for deployment in self.deployment_roots():
            roots = self.owners(deployment)
            for index, root in enumerate(roots):
                with self.subTest(tree=str(deployment), owner=root.parent.name):
                    content = root.read_text(encoding="utf-8")
                    numbers = [number for number, _, _ in steps(content)]
                    self.assertTrue(numbers, "Main path needs numbered steps")
                    self.assertEqual(numbers, list(range(1, len(numbers) + 1)))
                    if index < len(roots) - 1:
                        self.assertIn(roots[index + 1].resolve(), [link.target for link in links(root)],
                                      "Each completed capability must lead to the next stage")
            foundation = roots[0].read_text(encoding="utf-8")
            self.assertEqual([number for number, _, _ in steps(foundation)], [1, 2, 3, 4])
            legacy = {"before-starting-hosts-and-networks": 1,
                      "step-1-create-the-first-linux-template-manually": 2,
                      "step-2-prepare-the-bootstrap-execution-host": 3,
                      "step-3-publish-and-test-vm-templates": 4}
            for anchor, number in legacy.items():
                self.assertIn(anchor, anchors(foundation))
                self.assertEqual(step_at(foundation, anchors(foundation)[anchor]), number)

    def test_foundation_separates_bootstrap_from_hypervisor_guides(self):
        for deployment in self.deployment_roots():
            foundation = deployment / "foundation"
            bootstrap = foundation / "bootstrap/README.md"
            self.assertTrue(bootstrap.is_file())
            self.assertFalse((foundation / "proxmox/bootstrap.md").exists())
            self.assertIn("existing Linux host", bootstrap.read_text(encoding="utf-8"))
            for guide in ("step-1b-cluster-ha.md", "step-1c-sdn.md", "step-4c-proxlb.md",
                          "api-access.md", "templates.md"):
                self.assertTrue((foundation / "proxmox" / guide).is_file(), guide)
            for guide in (foundation / "bootstrap").glob("step-*.md"):
                self.assertTrue(guide.name.startswith("step-3"), str(guide))
                self.assertFalse((foundation / "proxmox" / guide.name).exists())

    def test_hardening_is_selected_at_first_service_deployment_not_hidden_in_foundation(self):
        for deployment in self.deployment_roots():
            security = deployment.parent / "administration/hosts/linux-security.md"
            root = deployment / "stage-1-software-intake/README.md"
            content = root.read_text(encoding="utf-8")
            self.assertTrue(security.is_file())
            self.assertFalse((deployment / "foundation/proxmox/host-security.md").exists())
            routes = [link for link in links(root) if link.target == security.resolve()]
            self.assertTrue(routes, "Stage 1 must select the shared Linux security guide")
            self.assertTrue(any(step_at(content, link.offset) == 4 for link in routes))
            choice = re.search(r"(?m)^#{2,6}\s+(?:Step\s+)?4b\b.*(?:\n(?!#{1,3}\s).*)*", content)
            self.assertIsNotNone(choice, "Hardening must be an explicit Step 4b choice")
            self.assertIn(security.resolve(), [link.target for link in links(root, choice[0])])

    def test_verified_worker_is_routed_after_the_issuer_with_real_installation_inputs(self):
        for deployment in self.deployment_roots():
            intake_root = deployment / "stage-1-software-intake"
            trust = deployment / "stage-3-trust/README.md"
            worker = trust.parent / "step-3b-verified-intake.md"
            consumers = trust.parent / "step-3b-verified-consumers.md"
            self.assertTrue(worker.is_file())
            self.assertTrue(consumers.is_file())
            self.assertFalse((intake_root / "verified-intake.md").exists())
            self.assertFalse((intake_root / "verified-consumers.md").exists())
            for guide in intake_root.rglob("*.md"):
                commands = "\n".join(re.findall(r"(?ms)^```(?:bash|sh|shell|console)\s*\n(.*?)^```", guide.read_text()))
                self.assertNotRegex(commands, r"scripts/deploy\.sh\s+(?:intake|syslog|foundation)\b",
                                    f"{guide.name} installs a later trust/logging-dependent capability")
                self.assertNotRegex(commands, r"scripts/init-local-files\.sh\s+--setup\s+intake\b")
            self.assertTrue(routed_from(trust, worker, 3), "Worker is selected after issuer acceptance")
            text = worker.read_text(encoding="utf-8")
            install = re.search(r"(?m)^bash scripts/deploy\.sh intake\s*$", text)
            self.assertIsNotNone(install, "Worker path needs the real combined VM/service installer")
            prerequisite_links = list(links(worker, text[:install.start()]))
            self.assertIn((deployment / "stage-2-logging/README.md").resolve(),
                          [link.target for link in prerequisite_links])
            self.assertTrue(any(link.target == trust.resolve() and
                                step_at(trust.read_text(), anchors(trust.read_text()).get(link.fragment, -1)) == 3
                                for link in prerequisite_links), "Issuer acceptance must precede worker installation")
            self.assertIn(consumers.resolve(), indexed_guides(trust))
            # Documentation must link to the supplied recipe, not merely label a baseline
            # or configuration example as a product installer. Generated cross-repo links
            # are checked against their real generated owners as well.
            recipes = [link.target for link in links(worker)
                       if link.target.as_posix().endswith("/ansible/playbooks/deployment/intake.yml")]
            self.assertTrue(recipes, "Worker must link its owning installation recipe")
            for recipe in recipes:
                self.assertTrue(recipe.is_file(), str(recipe))
                tier = recipe.parents[3]
                self.assertIn("intake", (tier / ".deployment-setups").read_text().splitlines())
                self.assertTrue((tier / "terraform/deployments/intake/main.tf").is_file())
