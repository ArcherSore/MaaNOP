import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import tempfile
import urllib.request
import zipfile

from configure import configure_ocr_model


ROOT = Path(__file__).parent.parent.resolve()
NARUTO_BASELINE_FIELDS = ("repository", "tag", "asset_name", "sha256")
PYTHON_BASELINE_FIELDS = ("version", "asset_name", "url", "sha256")
PAYLOAD_PATHS = ("interface.json", "resource", "agent", "README.md", "LICENSE", "python")
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


def load_baseline(path: Path) -> dict[str, dict[str, str]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    
    # 1. Load and validate windows_x64 (NarutoAutoGUI) baseline
    naruto = document.get("windows_x64")
    if not isinstance(naruto, dict):
        raise ValueError("Baseline must contain a windows_x64 object.")

    naruto_values: dict[str, str] = {}
    for field in NARUTO_BASELINE_FIELDS:
        value = naruto.get(field)
        if not isinstance(value, str) or not value or value.startswith("REPLACE_WITH_"):
            raise ValueError(f"windows_x64.{field} must contain a pinned release value.")
        naruto_values[field] = value

    if not SHA256_PATTERN.fullmatch(naruto_values["sha256"]):
        raise ValueError("windows_x64.sha256 must contain exactly 64 hexadecimal characters.")
    if not re.fullmatch(r"[^/\s]+/[^/\s]+", naruto_values["repository"]):
        raise ValueError("windows_x64.repository must use the owner/repository form.")
    if not naruto_values["tag"].startswith("v") or naruto_values["tag"].lower() == "latest":
        raise ValueError("windows_x64.tag must contain an explicit v-prefixed release tag.")
    naruto_asset = naruto_values["asset_name"]
    if Path(naruto_asset).name != naruto_asset or not naruto_asset.endswith(".zip") or re.search(r"[*?\[\]]", naruto_asset):
        raise ValueError("windows_x64.asset_name must be one exact ZIP file name without glob characters.")

    # 2. Load and validate python_embed_windows_x64 baseline
    py_baseline = document.get("python_embed_windows_x64")
    if not isinstance(py_baseline, dict):
        raise ValueError("Baseline must contain a python_embed_windows_x64 object.")

    py_values: dict[str, str] = {}
    for field in PYTHON_BASELINE_FIELDS:
        value = py_baseline.get(field)
        if not isinstance(value, str) or not value or value.startswith("REPLACE_WITH_"):
            raise ValueError(f"python_embed_windows_x64.{field} must contain a pinned value.")
        py_values[field] = value

    if not SHA256_PATTERN.fullmatch(py_values["sha256"]):
        raise ValueError("python_embed_windows_x64.sha256 must contain exactly 64 hexadecimal characters.")
    if not re.fullmatch(r"^\d+\.\d+\.\d+$", py_values["version"]):
        raise ValueError("python_embed_windows_x64.version must be an exact semantic version (e.g. 3.12.9).")
    py_asset = py_values["asset_name"]
    if Path(py_asset).name != py_asset or not py_asset.endswith(".zip") or re.search(r"[*?\[\]]", py_asset):
        raise ValueError("python_embed_windows_x64.asset_name must be one exact ZIP file name.")
    if not py_values["url"].startswith("http"):
        raise ValueError("python_embed_windows_x64.url must be a valid HTTP/HTTPS URL.")

    return {
        "windows_x64": naruto_values,
        "python_embed_windows_x64": py_values,
    }


def emit_baseline(path: Path, github_output: Path) -> None:
    baseline = load_baseline(path)
    naruto = baseline["windows_x64"]
    python_baseline = baseline["python_embed_windows_x64"]
    with github_output.open("a", encoding="utf-8", newline="\n") as output:
        for field in NARUTO_BASELINE_FIELDS:
            output.write(f"{field}={naruto[field]}\n")
        output.write(f"python_version={python_baseline['version']}\n")
        output.write(f"python_asset_name={python_baseline['asset_name']}\n")
        output.write(f"python_url={python_baseline['url']}\n")
        output.write(f"python_sha256={python_baseline['sha256']}\n")
    print(f"Pinned NarutoAutoGUI baseline: {naruto['repository']}@{naruto['tag']}")
    print(f"NarutoAutoGUI Asset: {naruto['asset_name']}")
    print(f"NarutoAutoGUI SHA256: {naruto['sha256'].lower()}")
    print(f"Pinned Python Embed baseline: {python_baseline['version']}")
    print(f"Python Asset: {python_baseline['asset_name']}")
    print(f"Python SHA256: {python_baseline['sha256'].lower()}")


def verify_archive(archive: Path, baseline_path: Path) -> dict[str, str]:
    baseline = load_baseline(baseline_path)["windows_x64"]
    if archive.name != baseline["asset_name"]:
        raise ValueError(f"Expected asset {baseline['asset_name']}, got {archive.name}.")
    actual = sha256(archive)
    if actual.lower() != baseline["sha256"].lower():
        raise ValueError(f"SHA256 mismatch: expected {baseline['sha256'].lower()}, got {actual.lower()}.")
    print(f"NarutoAutoGUI asset SHA256 verified: {actual.lower()}")
    return baseline


def ensure_python_archive(baseline_path: Path, python_archive: Path | None = None) -> Path:
    py_baseline = load_baseline(baseline_path)["python_embed_windows_x64"]
    expected_sha256 = py_baseline["sha256"].lower()

    if python_archive and python_archive.is_file():
        actual_sha256 = sha256(python_archive).lower()
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"Python archive SHA256 mismatch: expected {expected_sha256}, got {actual_sha256}."
            )
        print(f"Python embed archive verified from {python_archive}")
        return python_archive.resolve()

    cache_dir = ROOT / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    target_path = cache_dir / py_baseline["asset_name"]

    if target_path.is_file() and sha256(target_path).lower() == expected_sha256:
        print(f"Python embed archive found in cache: {target_path}")
        return target_path.resolve()

    print(f"Downloading Python embed from {py_baseline['url']} ...")
    req = urllib.request.Request(py_baseline["url"], headers={"User-Agent": "MaaNOP-Packager"})
    with urllib.request.urlopen(req) as resp, target_path.open("wb") as out_file:
        shutil.copyfileobj(resp, out_file)

    actual_sha256 = sha256(target_path).lower()
    if actual_sha256 != expected_sha256:
        raise ValueError(
            f"Downloaded Python archive SHA256 mismatch: expected {expected_sha256}, got {actual_sha256}."
        )
    print(f"Downloaded and verified Python embed archive: {target_path}")
    return target_path.resolve()


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


def setup_python_runtime(install: Path, python_archive: Path) -> None:
    install_dir = install.resolve()
    py_dir = install_dir / "python"
    if py_dir.exists():
        shutil.rmtree(py_dir)
    py_dir.mkdir(parents=True)

    with zipfile.ZipFile(python_archive) as archive:
        validate_archive_members(archive)
        archive.extractall(py_dir)

    pth_files = list(py_dir.glob("*._pth"))
    if not pth_files:
        raise ValueError("No ._pth file found in extracted Python runtime.")
    
    pth_file = pth_files[0]
    zip_name = pth_file.stem + ".zip"
    pth_content = f"{zip_name}\n.\nLib/site-packages\nsite-packages\n../agent\nimport site\n"
    pth_file.write_text(pth_content, encoding="utf-8")
    print(f"Configured {pth_file.name} for site-packages and agent import.")

    py_exe = (py_dir / "python.exe").resolve()
    if not py_exe.is_file():
        raise ValueError("python.exe missing in extracted Python runtime.")

    # Bootstrap pip using get-pip.py
    get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
    get_pip_path = (py_dir / "get-pip.py").resolve()
    print("Downloading get-pip.py ...")
    req = urllib.request.Request(get_pip_url, headers={"User-Agent": "MaaNOP-Packager"})
    with urllib.request.urlopen(req) as resp, get_pip_path.open("wb") as out_file:
        shutil.copyfileobj(resp, out_file)

    print("Bootstrapping pip in bundled Python runtime ...")
    res = subprocess.run(
        [str(py_exe), str(get_pip_path), "--no-warn-script-location"],
        cwd=str(install_dir),
        capture_output=True,
        text=True,
    )
    if get_pip_path.exists():
        get_pip_path.unlink()
    if res.returncode != 0:
        raise RuntimeError(f"Failed to bootstrap pip:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")

    requirements_path = (ROOT / "agent" / "requirements.txt").resolve()
    if not requirements_path.is_file():
        raise ValueError(f"Agent requirements file not found: {requirements_path}")

    print(f"Installing Agent requirements from {requirements_path} ...")
    res = subprocess.run(
        [str(py_exe), "-m", "pip", "install", "--no-warn-script-location", "-r", str(requirements_path)],
        cwd=str(install_dir),
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise RuntimeError(f"Failed to install Agent requirements:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")

    print("Bundled Python runtime and Agent dependencies installed successfully.")


def overlay_payload(install: Path, package_version: str) -> None:
    install_dir = install.resolve()
    configure_ocr_model()
    shutil.copytree(ROOT / "assets" / "resource", install_dir / "resource", dirs_exist_ok=True)
    shutil.copytree(
        ROOT / "agent",
        install_dir / "agent",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        dirs_exist_ok=True,
    )
    for name in ("README.md", "LICENSE"):
        shutil.copy2(ROOT / name, install_dir / name)
    shutil.copy2(ROOT / "assets" / "interface.json", install_dir / "interface.json")

    interface_path = install_dir / "interface.json"
    with interface_path.open("r", encoding="utf-8") as stream:
        interface = json.load(stream)
    interface["version"] = package_version
    if "agent" not in interface or not isinstance(interface["agent"], dict):
        interface["agent"] = {}
    interface["agent"]["child_exec"] = "./python/python.exe"
    with interface_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(interface, stream, ensure_ascii=False, indent=4)
        stream.write("\n")
    print(f"Packaged interface.json updated with version={package_version} and child_exec=./python/python.exe")


def run_smoke_test(install: Path) -> None:
    install_dir = install.resolve()
    py_exe = (install_dir / "python" / "python.exe").resolve()
    if not py_exe.is_file():
        raise ValueError(f"Bundled Python executable missing: {py_exe}")

    if platform.system() != "Windows":
        print(f"Skipping smoke test execution: host OS is {platform.system()}, not Windows.")
        return

    smoke_script_code = """
import sys
from pathlib import Path

# Add agent directory to sys.path
agent_dir = (Path(__file__).resolve().parent / "agent").resolve()
if str(agent_dir) not in sys.path:
    sys.path.insert(0, str(agent_dir))

# 1. Import maa
import maa
print(f"[SmokeTest] maa imported successfully: {getattr(maa, '__version__', 'ok')}")

# 2. Import AgentServer
from maa.agent.agent_server import AgentServer
print(f"[SmokeTest] AgentServer imported successfully: {AgentServer}")

# 3. Import all MaaNOP Agent modules
import action_common
import action_login
import action_shopping
import action_training
import common
import constants
import reco_login
import reco_shopping
import reco_training
import main
print("[SmokeTest] All MaaNOP Agent modules imported successfully.")

# 4. Test Tasker.set_log_dir
from maa.tasker import Tasker
res = Tasker.set_log_dir("./debug")
print(f"[SmokeTest] Tasker.set_log_dir result: {res}")
"""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp_file:
        tmp_file.write(smoke_script_code)
        tmp_script = Path(tmp_file.name).resolve()

    try:
        res = subprocess.run(
            [str(py_exe), str(tmp_script)],
            cwd=str(install_dir),
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            raise RuntimeError(
                f"Smoke test failed on bundled Python runtime:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
            )
        print(f"Smoke test output:\n{res.stdout.strip()}")
        print("Smoke test passed successfully.")
    finally:
        if tmp_script.exists():
            tmp_script.unlink()
        debug_dir = install_dir / "debug"
        if debug_dir.exists():
            shutil.rmtree(debug_dir, ignore_errors=True)


def compose(
    archive: Path,
    baseline_path: Path,
    install: Path,
    package_version: str,
    python_archive: Path | None = None,
) -> None:
    verify_archive(archive, baseline_path)
    verified_py_archive = ensure_python_archive(baseline_path, python_archive)
    if install.exists():
        raise ValueError(f"Install directory must not already exist: {install}")
    install.mkdir(parents=True)
    with zipfile.ZipFile(archive) as package:
        validate_archive_members(package)
        package.extractall(install)
    validate_naruto_base(install)
    setup_python_runtime(install, verified_py_archive)
    overlay_payload(install, package_version)
    run_smoke_test(install)
    print(f"Windows x64 package composed successfully at {install}")


def is_under(relative_path: str, parent: str) -> bool:
    return relative_path == parent or relative_path.startswith(f"{parent}/")


def validate_python_boundary(install: Path) -> None:
    forbidden = []
    for path in install.rglob("*"):
        relative = path.relative_to(install).as_posix()
        lower_name = path.name.lower()
        if path.is_dir():
            if lower_name in {"site-packages", "python"} and not is_under(relative, "python"):
                forbidden.append(relative)
            elif lower_name == "__pycache__" and not (is_under(relative, "python") or is_under(relative, "agent")):
                forbidden.append(relative)
        elif path.is_file():
            if (lower_name.endswith(".pyd") or re.fullmatch(r"python(?:w|\d.*)?\.exe", lower_name)) and not is_under(relative, "python"):
                forbidden.append(relative)
            elif re.fullmatch(r"python\d+\.dll", lower_name) and not is_under(relative, "python"):
                forbidden.append(relative)
            elif path.suffix.lower() == ".py" and not (is_under(relative, "agent") or is_under(relative, "python")):
                forbidden.append(relative)
    if forbidden:
        raise ValueError(f"Unexpected Python runtime or script files outside boundaries: {', '.join(forbidden)}")


def validate_final_package(archive: Path, baseline_path: Path, install: Path) -> None:
    verify_archive(archive, baseline_path)
    # Clean up runtime generated debug directory if present
    debug_dir = install / "debug"
    if debug_dir.exists():
        shutil.rmtree(debug_dir, ignore_errors=True)

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

    require_file(install, "python/python.exe")
    require_file(install, "python/python3.dll")
    require_file(install, "agent/requirements.txt")

    with (install / "interface.json").open("r", encoding="utf-8") as stream:
        interface = json.load(stream)
    agent = interface.get("agent")
    if not isinstance(agent, dict) or agent.get("child_exec") != "./python/python.exe":
        raise ValueError('interface.json must set agent.child_exec = "./python/python.exe".')

    forbidden_mfa = [path for path in install.rglob("*") if "mfaavalonia" in path.name.lower()]
    if forbidden_mfa:
        names = ", ".join(path.relative_to(install).as_posix() for path in forbidden_mfa)
        raise ValueError(f"MFAAvalonia content is forbidden in Windows x64 package: {names}")
    validate_python_boundary(install)

    misplaced_framework = []
    for path in install.rglob("*"):
        relative = path.relative_to(install).as_posix()
        if (
            path.is_file()
            and path.name.lower().startswith("maaframework")
            and not (is_under(relative, "worker") or is_under(relative, "python"))
        ):
            misplaced_framework.append(relative)
    if misplaced_framework:
        raise ValueError(f"MaaFramework runtime exists outside worker/ or python/: {', '.join(misplaced_framework)}")

    run_smoke_test(install)
    print("Final Windows x64 package validation passed.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    baseline_parser = subparsers.add_parser("baseline")
    baseline_parser.add_argument("--config", type=Path, required=True)
    baseline_parser.add_argument("--github-output", type=Path, required=True)

    compose_parser = subparsers.add_parser("compose")
    compose_parser.add_argument("--archive", type=Path, required=True)
    compose_parser.add_argument("--baseline", type=Path, required=True)
    compose_parser.add_argument("--install", type=Path, required=True)
    compose_parser.add_argument("--package-version", required=True)
    compose_parser.add_argument("--python-archive", type=Path, required=False, default=None)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--archive", type=Path, required=True)
    validate_parser.add_argument("--baseline", type=Path, required=True)
    validate_parser.add_argument("--install", type=Path, required=True)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "baseline":
        emit_baseline(args.config, args.github_output)
    elif args.command == "compose":
        compose(args.archive, args.baseline, args.install, args.package_version, args.python_archive)
    else:
        validate_final_package(args.archive, args.baseline, args.install)


if __name__ == "__main__":
    main()
