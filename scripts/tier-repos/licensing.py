"""Preserve upstream attribution without selecting a downstream project license."""

from documentation import AUTO_DOCS
from payload import read_file


def copy_attribution(writer, upstream, name):
    legacy_license = writer.hashes.pop("LICENSE", None)
    if legacy_license is not None or (writer.root / "LICENSE").exists():
        writer.owned_paths.add("LICENSE")
    if legacy_license is not None:
        print(f"Project LICENSE left unchanged at {writer.root / 'LICENSE'}; "
              "review its scope manually. Project licensing is no longer managed by the kit.")

    license_text = read_file(upstream / "LICENSE")
    notice = (
        "Upstream attribution\n\n"
        "Source: https://github.com/Rexus/homelab\n\n"
        "The following notice applies only to material copied or derived from the\n"
        "upstream deployment kit, including automation, examples, and document templates.\n"
        "It does not select a project-wide license or license independently authored\n"
        "project content. Project licensing is determined by the repository owners.\n\n"
        + license_text
    )
    writer.write("UPSTREAM-NOTICE", notice)
    if name == "architecture":
        writer.write(f"{AUTO_DOCS}/LICENSE", license_text)
