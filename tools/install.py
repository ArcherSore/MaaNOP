import argparse
import ctypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

from configure import configure_ocr_model


ROOT = Path(__file__).parent.parent.resolve()
NATIVE = "worker/runtimes/win-x64/native"


def worker_framework_version(install: Path) -> str:
    """The Agent loads the GUI's MaaFramework, so the GUI decides which maafw binding the package needs."""
    framework = ctypes.WinDLL(str(install / NATIVE / "MaaFramework.dll"))
    framework.MaaVersion.restype = ctypes.c_char_p
    return framework.MaaVersion().decode().removeprefix("v")


def install_python(install: Path, version: str, maafw_version: str) -> None:
    python_dir = install / "python"
    python_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="maanop-python-") as temp:
        temp_dir = Path(temp)
        archive = temp_dir / "python.zip"
        urllib.request.urlretrieve(
            f"https://www.python.org/ftp/python/{version}/python-{version}-embed-amd64.zip",
            archive,
        )
        with zipfile.ZipFile(archive) as package:
            package.extractall(python_dir)

        pth_file = next(python_dir.glob("*._pth"))
        pth_file.write_text(
            f"{pth_file.stem}.zip\n.\nLib/site-packages\n../agent\nimport site\n",
            encoding="utf-8",
        )
        python = python_dir / "python.exe"
        get_pip = temp_dir / "get-pip.py"
        urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", get_pip)
        subprocess.run([str(python), str(get_pip), "--no-warn-script-location"], check=True)
        subprocess.run(
            [str(python), "-m", "pip", "install", "--no-warn-script-location", "-r", str(ROOT / "agent/requirements.txt")],
            check=True,
        )
        subprocess.run(
            [str(python), "-m", "pip", "install", "--no-warn-script-location", f"maafw=={maafw_version}"],
            check=True,
        )


def install_payload(install: Path, version: str) -> None:
    configure_ocr_model()
    shutil.copytree(ROOT / "assets/resource", install / "resource", dirs_exist_ok=True)
    shutil.copytree(
        ROOT / "agent",
        install / "agent",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        dirs_exist_ok=True,
    )
    shutil.copytree(ROOT / "assets/locales", install / "locales", dirs_exist_ok=True)
    for name in ("README.md", "LICENSE"):
        shutil.copy2(ROOT / name, install / name)

    interface = json.loads((ROOT / "assets/interface.json").read_text(encoding="utf-8"))
    interface["version"] = version
    interface["agent"]["child_exec"] = "./python/python.exe"
    (install / "interface.json").write_text(
        json.dumps(interface, ensure_ascii=False, indent=4) + "\n", encoding="utf-8"
    )


def trim_python(install: Path) -> None:
    """Share the packaged MaaFramework for every Python entry point, independently of the launcher."""
    python_dir = install / "python"
    site_packages = python_dir / "Lib/site-packages"
    # Embedded Python enables import site. Keep this package-layout choice in MaaNOP, not in the GUI.
    (site_packages / "sitecustomize.py").write_text(
        "import os\nfrom pathlib import Path\nimport sys\n\n"
        f"os.environ['MAAFW_BINARY_PATH'] = str(Path(sys.executable).resolve().parent.parent / {NATIVE!r})\n",
        encoding="utf-8",
    )
    removed = [site_packages / "maa/bin", python_dir / "Scripts"]
    for pattern in ("MaaAgentBinary*", "pip", "pip-*.dist-info"):
        removed += site_packages.glob(pattern)
    removed += (site_packages / "numpy").rglob("tests")
    removed += python_dir.rglob("__pycache__")
    for path in removed:
        shutil.rmtree(path, ignore_errors=True)


def verify_agent(install: Path) -> None:
    """Check both entry points without a GUI-provided native library path."""
    environment = os.environ.copy()
    environment.pop("MAAFW_BINARY_PATH", None)
    scripts = (
        "import main; print('Packaged Agent imports passed.')",
        "import pretask_launch; from maa.toolkit import Toolkit; "
        "Toolkit.find_desktop_windows(); print('Packaged pretask and Toolkit passed.')",
    )
    # AgentServer and Toolkit use different MaaFramework contexts, as in the real separate processes.
    for script in scripts:
        subprocess.run(
            [str(install / "python/python.exe"), "-B", "-c", script],
            cwd=install,
            env=environment,
            check=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Add MaaNOP resources and embedded Python to the Windows x64 GUI package.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--python-version", required=True)
    parser.add_argument("--install", type=Path, default=ROOT / "install")
    args = parser.parse_args()
    install = args.install.resolve()

    for name in ("NarutoAutoGUI.exe", "worker/NarutoAutoWorker.exe"):
        if not (install / name).is_file():
            raise FileNotFoundError(f"Extract the NarutoAutoGUI Windows x64 release first: missing {name}")

    install_python(install, args.python_version, worker_framework_version(install))
    install_payload(install, args.version)
    trim_python(install)
    verify_agent(install)
    print(f"MaaNOP Windows x64 package ready: {install}")


if __name__ == "__main__":
    main()
