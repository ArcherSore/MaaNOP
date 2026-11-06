import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

from configure import configure_ocr_model


ROOT = Path(__file__).parent.parent.resolve()


def install_python(install: Path, version: str) -> None:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Add MaaNOP resources and embedded Python to the Windows x64 GUI package.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--python-version", required=True)
    parser.add_argument("--install", type=Path, default=ROOT / "install")
    args = parser.parse_args()
    install = args.install.resolve()

    for name in ("NarutoAutoGUI.exe", "libs/coreclr.dll", "worker/NarutoAutoWorker.exe", "worker/coreclr.dll"):
        if not (install / name).is_file():
            raise FileNotFoundError(f"Extract the self-contained NarutoAutoGUI Windows x64 release first: missing {name}")

    install_python(install, args.python_version)
    install_payload(install, args.version)
    subprocess.run(
        [str(install / "python/python.exe"), "-c", "import maa; from maa.agent.agent_server import AgentServer; import main; print('Packaged Python and Agent imports passed.')"],
        cwd=install,
        check=True,
    )
    print(f"MaaNOP Windows x64 package ready: {install}")


if __name__ == "__main__":
    main()
