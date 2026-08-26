import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import zipfile

from configure import configure_ocr_model


ROOT = Path(__file__).parent.parent.resolve()
BASELINE_FIELDS = ("repository", "tag", "asset_name", "sha256")
PAYLOAD_PATHS = ("interface.json", "resource", "agent", "README.md", "LICENSE")
NARUTO_REQUIRED_FILES = (
    "NarutoAutoGUI.exe",
    "NarutoAutoGUI.dll",
    "worker/NarutoAutoWorker.exe",
    "worker/NarutoAutoWorker.dll",
    "worker/runtimes/win-x64/native/MaaFramework.dll",
    "worker/runtimes/win-x64/native/MaaWin32ControlUnit.dll",
)
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_baseline(path: Path) -> dict[str, str]:
    document = json.loads(path.read_text(encoding="utf-8"))
    baseline = document.get("windows_x64")
    if not isinstance(baseline, dict):
        raise ValueError("Baseline must contain a windows_x64 object.")

    values = {}
    for field in BASELINE_FIELDS:
        value = baseline.get(field)
        if not isinstance(value, str) or not value or value.startswith("REPLACE_WITH_"):
            raise ValueError(f"windows_x64.{field} must contain a pinned release value.")
        values[field] = value

    if not SHA256_PATTERN.fullmatch(values["sha256"]):
        raise ValueError("windows_x64.sha256 must contain exactly 64 hexadecimal characters.")
    if not re.fullmatch(r"[^/\s]+/[^/\s]+", values["repository"]):
        raise ValueError("windows_x64.repository must use the owner/repository form.")
    if not values["tag"].startswith("v") or values["tag"].lower() == "latest":
        raise ValueError("windows_x64.tag must contain an explicit v-prefixed release tag.")
    asset_name = values["asset_name"]
    if Path(asset_name).name != asset_name or not asset_name.endswith(".zip") or re.search(r"[*?\[\]]", asset_name):
        raise ValueError("windows_x64.asset_name must be one exact ZIP file name without glob characters.")
    return values


def emit_baseline(path: Path, github_output: Path) -> None:
    baseline = load_baseline(path)
    with github_output.open("a", encoding="utf-8", newline="\n") as output:
        for field in BASELINE_FIELDS:
            output.write(f"{field}={baseline[field]}\n")
    print(f"Pinned NarutoAutoGUI baseline: {baseline['repository']}@{baseline['tag']}")
    print(f"Asset: {baseline['asset_name']}")
    print(f"SHA256: {baseline['sha256'].lower()}")


def verify_archive(archive: Path, baseline_path: Path) -> dict[str, str]:
    baseline = load_baseline(baseline_path)
    if archive.name != baseline["asset_name"]:
        raise ValueError(f"Expected asset {baseline['asset_name']}, got {archive.name}.")
    actual = sha256(archive)
    if actual.lower() != baseline["sha256"].lower():
        raise ValueError(f"SHA256 mismatch: expected {baseline['sha256'].lower()}, got {actual.lower()}.")
    print(f"NarutoAutoGUI asset SHA256 verified: {actual.lower()}")
    return baseline


def validate_archive_members(archive: zipfile.ZipFile) -> None:
    for member in archive.infolist():
        name = member.filename.replace("\\", "/")
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or (path.parts and ":" in path.parts[0]):
            raise ValueError(f"Unsafe archive member: {member.filename}")
        file_type = (member.external_attr >> 16) & 0o170000
        if file_type == stat.S_IFLNK:
            raise ValueError(f"Archive symlink is not allowed: {member.filename}")


def require_file(root: Path, relative_path: str) -> None:
    path = root / relative_path
    if not path.is_file():
        raise ValueError(f"Required package file is missing: {relative_path}")


def validate_naruto_base(root: Path, reject_payload_collisions: bool = True) -> None:
    for relative_path in NARUTO_REQUIRED_FILES:
        require_file(root, relative_path)
    if reject_payload_collisions:
        for relative_path in PAYLOAD_PATHS:
            if (root / relative_path).exists():
                raise ValueError(f"NarutoAutoGUI base collides with MaaNOP-owned path: {relative_path}")


def file_manifest(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def overlay_payload(install: Path, package_version: str) -> None:
    configure_ocr_model()
    shutil.copytree(ROOT / "assets" / "resource", install / "resource")
    shutil.copytree(
        ROOT / "agent",
        install / "agent",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    for name in ("README.md", "LICENSE"):
        shutil.copy2(ROOT / name, install / name)
    shutil.copy2(ROOT / "assets" / "interface.json", install / "interface.json")

    interface_path = install / "interface.json"
    with interface_path.open("r", encoding="utf-8") as stream:
        interface = json.load(stream)
    interface["version"] = package_version
    with interface_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(interface, stream, ensure_ascii=False, indent=4)
        stream.write("\n")


def compose(archive: Path, baseline_path: Path, install: Path, package_version: str) -> None:
    verify_archive(archive, baseline_path)
    if install.exists():
        raise ValueError(f"Install directory must not already exist: {install}")
    install.mkdir(parents=True)
    with zipfile.ZipFile(archive) as package:
        validate_archive_members(package)
        package.extractall(install)
    validate_naruto_base(install)
    overlay_payload(install, package_version)
    print(f"Windows x64 package composed at {install}")


def is_under(relative_path: str, parent: str) -> bool:
    return relative_path == parent or relative_path.startswith(f"{parent}/")


def validate_python_boundary(install: Path) -> None:
    forbidden = []
    for path in install.rglob("*"):
        relative = path.relative_to(install).as_posix()
        lower_name = path.name.lower()
        if path.is_dir() and lower_name in {"site-packages", "__pycache__", "python"}:
            forbidden.append(relative)
        if path.is_file() and (lower_name.endswith(".pyd") or re.fullmatch(r"python(?:w|\d.*)?\.exe", lower_name)):
            forbidden.append(relative)
        if path.is_file() and re.fullmatch(r"python\d+\.dll", lower_name):
            forbidden.append(relative)
        if path.is_file() and path.suffix.lower() == ".py" and not is_under(relative, "agent"):
            forbidden.append(relative)
    if forbidden:
        raise ValueError(f"Bundled Python runtime or unexpected Python source found: {', '.join(forbidden)}")


def validate_final_package(archive: Path, baseline_path: Path, install: Path) -> None:
    verify_archive(archive, baseline_path)
    with zipfile.ZipFile(archive) as package:
        validate_archive_members(package)
        with tempfile.TemporaryDirectory(prefix="naruto-base-") as temp_dir:
            base_dir = Path(temp_dir)
            package.extractall(base_dir)
            validate_naruto_base(base_dir)
            base_manifest = file_manifest(base_dir)

    final_manifest = file_manifest(install)
    changed = [path for path, digest in base_manifest.items() if final_manifest.get(path) != digest]
    if changed:
        raise ValueError(f"MaaNOP overlay modified NarutoAutoGUI-owned files: {', '.join(changed)}")
    unexpected = [
        path for path in final_manifest.keys() - base_manifest.keys()
        if not any(is_under(path, parent) for parent in PAYLOAD_PATHS)
    ]
    if unexpected:
        raise ValueError(f"Files outside the MaaNOP overlay boundary were added: {', '.join(unexpected)}")

    validate_naruto_base(install, reject_payload_collisions=False)
    for relative_path in PAYLOAD_PATHS:
        if not (install / relative_path).exists():
            raise ValueError(f"MaaNOP-owned payload is missing: {relative_path}")

    with (install / "interface.json").open("r", encoding="utf-8") as stream:
        interface = json.load(stream)
    agent = interface.get("agent")
    if not isinstance(agent, dict) or agent.get("child_exec") != "python":
        raise ValueError('interface.json must keep agent.child_exec = "python".')

    forbidden_mfa = [path for path in install.rglob("*") if "mfaavalonia" in path.name.lower()]
    if forbidden_mfa:
        names = ", ".join(path.relative_to(install).as_posix() for path in forbidden_mfa)
        raise ValueError(f"MFAAvalonia content is forbidden in Windows x64 package: {names}")
    validate_python_boundary(install)

    misplaced_framework = []
    for path in install.rglob("*"):
        relative = path.relative_to(install).as_posix()
        if path.is_file() and path.name.lower().startswith("maaframework") and not is_under(relative, "worker"):
            misplaced_framework.append(relative)
    if misplaced_framework:
        raise ValueError(f"MaaFramework runtime exists outside worker/: {', '.join(misplaced_framework)}")
    print("Final Windows x64 package validation passed.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    baseline_parser = subparsers.add_parser("baseline")
    baseline_parser.add_argument("--config", type=Path, required=True)
    baseline_parser.add_argument("--github-output", type=Path, required=True)

    for command in ("compose", "validate"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--archive", type=Path, required=True)
        command_parser.add_argument("--baseline", type=Path, required=True)
        command_parser.add_argument("--install", type=Path, required=True)
        if command == "compose":
            command_parser.add_argument("--package-version", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "baseline":
        emit_baseline(args.config, args.github_output)
    elif args.command == "compose":
        compose(args.archive, args.baseline, args.install, args.package_version)
    else:
        validate_final_package(args.archive, args.baseline, args.install)


if __name__ == "__main__":
    main()
