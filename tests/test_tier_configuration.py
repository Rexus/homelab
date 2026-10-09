"""Parse publishable configuration and verify local cluster references."""

import json
import unittest

import yaml

from tier_repo_test_support import UPSTREAM


def unique_mapping(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate configuration key: {key}")
        result[key] = value
    return result


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def yaml_mapping(loader, node):
    loader.flatten_mapping(node)
    return unique_mapping((loader.construct_object(key), loader.construct_object(value))
                          for key, value in node.value)


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, yaml_mapping)


class ConfigurationConsistency(unittest.TestCase):
    def test_publishable_yaml_and_json_have_unique_keys(self):
        for name in ("tier-0", "tier-1", "tier-2", "shared", "scripts/tier-repos"):
            for path in (UPSTREAM / name).rglob("*"):
                if not path.is_file() or any(part.startswith(".") for part in path.relative_to(UPSTREAM).parts):
                    continue
                is_example = path.name.endswith((".yml.example", ".yaml.example"))
                is_yaml = path.suffix in (".yml", ".yaml")
                if is_yaml and ("inventory" in path.parts or "group_vars" in path.parts):
                    continue
                with self.subTest(path=path):
                    if is_example or is_yaml:
                        list(yaml.load_all(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader))
                    elif path.suffix == ".json":
                        json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_mapping)

    def test_cluster_starters_only_reference_existing_local_resources(self):
        for tier in ("tier-0", "tier-1", "tier-2"):
            root = UPSTREAM / tier / "clusters"
            for path in root.rglob("kustomization.yaml"):
                config = yaml.safe_load(path.read_text())
                self.assertEqual(config["kind"], "Kustomization", path)
                for resource in config.get("resources", []):
                    target = (path.parent / resource).resolve()
                    self.assertTrue(target.is_relative_to(root), (path, resource))
                    self.assertTrue(target.is_file() or (target / "kustomization.yaml").is_file(),
                                    (path, resource))


if __name__ == "__main__":
    unittest.main()
