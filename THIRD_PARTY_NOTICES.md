# Third-Party Notices

This file lists third-party software, assets, and components used by or distributed with MaaNOP, together with the licenses and attribution each requires. MaaNOP itself is licensed under `GPL-3.0-only` (see `LICENSE` and the License section of `README.md`). Starting with v2.2.0, MaaNOP is `GPL-3.0-only`; releases through v2.1.0 were published under the MIT License and remain so. The components below retain their **own** licenses; they are **not** re-licensed under the GPL by being distributed alongside MaaNOP.

---

## MaaPracticeBoilerplate (template origin)

- **Upstream:** <https://github.com/MaaXYZ/MaaPracticeBoilerplate>
- **License:** MIT License — `Copyright (c) 2024 MaaXYZ`
- **Full license text:** [`licenses/MaaPracticeBoilerplate-MIT.txt`](./licenses/MaaPracticeBoilerplate-MIT.txt)

MaaNOP was originally created from the MaaPracticeBoilerplate template. Files that still reflect the template's baseline (for example the generic installer `tools/install.py`, the OCR configurator `configure.py`, the resource checker `check_resource.py`, the MaaFramework pipeline/interface JSON Schemas under `deps/tools/`, the git-cliff configuration, the pre-commit / formatting configuration, and the issue templates) were inherited from that template. The original MIT copyright and permission notice of MaaXYZ are preserved unchanged in the file referenced above. Later MaaNOP-specific development on top of the template is licensed under the project's overall `GPL-3.0-only` terms.

## MaaFramework

- **Upstream:** <https://github.com/MaaXYZ/MaaFramework>
- **License:** GNU Lesser General Public License v3.0 (LGPL-3.0). See the upstream repository's `LICENSE` for the exact SPDX expression.
- **How MaaNOP depends on / distributes it:**
  - At **development / CI time** (non-Windows-x64 targets) MaaFramework is downloaded as a prebuilt dependency into `deps/` (see `.github/workflows/install.yml`, pinned to `MAAFW_VERSION`).
  - In the **Windows x64 release** the MaaFramework runtime (`MaaFramework.dll` and companion control-unit / toolkit libraries) is bundled inside the separate `NarutoAutoGUI` base package (`worker/runtimes/win-x64/native/`), which is pulled as a pinned release asset and overlaid with MaaNOP content (see `.github/package-baselines.json` and `tools/package_windows_x64.py`). MaaNOP does not modify or re-license those binaries.

MaaFramework remains licensed under LGPL-3.0. It is **not** claimed to be re-licensed under GPL-3.0. The combination is permitted because a GPL-3.0-covered work may link to / combine with an LGPL-3.0 library under the LGPL's terms.

## MaaCommonAssets

- **Upstream:** <https://github.com/MaaXYZ/MaaCommonAssets>
- **License:** MIT License — `Copyright (c) 2023 MAA`
- **In this repository:** git submodule at `assets/MaaCommonAssets` (see `.gitmodules`).
- **How it is used:** Provides the OCR models. `configure.py` copies the PaddleOCR PP-OCR models from `assets/MaaCommonAssets/OCR/` into `assets/resource/model/ocr/`, which is then shipped in the release resource bundle.

The MIT notice of MAA is retained with the submodule. The bundled OCR models also carry their own per-model `README.md` describing the upstream PaddleOCR source (see below).

## PaddleOCR (OCR model upstream)

- **Upstream:** <https://github.com/PaddlePaddle/PaddleOCR>
- **License:** Apache License 2.0 (Apache-2.0) for the PaddleOCR project.
- **In this repository:** The OCR detection/recognition ONNX models (`det.onnx`, `rec.onnx`, `keys.txt`) used by MaaNOP are redistributed via `MaaCommonAssets` (see above). The per-model `README.md` files under `assets/MaaCommonAssets/OCR/` and `assets/resource/model/ocr/README.md` document the PaddleOCR origin and model variants (PP-OCRv3/4/5/6).

Attribution to PaddlePaddle/PaddleOCR is retained as provided by MaaCommonAssets. Apache-2.0 is compatible with GPL-3.0.

## Python runtime (Windows x64 release)

- **Upstream:** <https://www.python.org/downloads/>
- **License:** Python Software Foundation (PSF) License Agreement for Python.
- **How it is distributed:** The Windows x64 release embeds a pinned CPython embeddable package (`python_embed_windows_x64` baseline in `.github/package-baselines.json`), extracted into the release `python/` directory, and is used to run the MaaNOP agent (`agent/`).

The PSF License is GPL-compatible. The embeddable archive carries its own `LICENSE.txt` and license files internally; those travel with the extracted runtime.

## maafw (MaaFramework Python binding)

- **Upstream:** distributed via PyPI as `maafw` (<https://pypi.org/project/maafw/>), by MaaXYZ.
- **License:** follows the MaaFramework license terms (LGPL-3.0; verify at upstream for the exact SPDX expression).
- **How it is used:** pinned in `agent/requirements.txt` (`maafw==5.12.3`) and installed into the bundled Python runtime of the Windows x64 release so the MaaNOP agent can drive MaaFramework.

## NarutoAutoGUI (Windows graphical front-end and bundled runtime)

- **Upstream:** <https://github.com/ArcherSore/NarutoAutoGUI>
- **License:** see the NarutoAutoGUI repository / its release package. NarutoAutoGUI is a separate project.
- **How it is distributed:** The Windows x64 release is composed on top of a pinned `NarutoAutoGUI` release asset (`.github/package-baselines.json`). That base package carries, in addition to the GUI binaries, several third-party runtime libraries bundled by NarutoAutoGUI itself, including (non-exhaustive):

  | Component | Upstream | License (typical) |
  | --- | --- | --- |
  | ONNX Runtime | <https://github.com/microsoft/onnxruntime> | MIT |
  | OpenCV | <https://github.com/opencv/opencv> | Apache-2.0 |
  | .NET runtime (self-contained) | <https://github.com/dotnet/runtime> | MIT (see .NET LICENSE for details) |
  | ViGEmClient | <https://github.com/ViGEm/ViGEmClient> | MIT |
  | DirectML | Microsoft | MIT |

  These are bundled **inside the NarutoAutoGUI base package**, not added by MaaNOP's overlay. License compliance for that base package (including any required license/notice files for LGPL components such as MaaFramework) is the responsibility of the NarutoAutoGUI distribution. MaaNOP's own overlay additionally ships `LICENSE`, `README.md`, `THIRD_PARTY_NOTICES.md`, and the `licenses/` directory (see `tools/package_windows_x64.py`).

## Development-only tooling (not distributed in releases)

The following are used only for development / CI and are **not** shipped in release packages; their notices are not required to accompany the release. They are listed for completeness:

- `@nekosu/maa-tools` (npm, resource checker) and its transitive npm dependencies — permissive licenses (MIT / ISC / Apache-2.0 / BlueOak-1.0.0 / BSD-2-Clause / CC0-1.0), recorded in `package-lock.json`.
- `prettier`, `prettier-plugin-multiline-arrays`, `markdownlint-cli2`, `oxipng` via `pre-commit`.

---

## License compatibility summary

All distributed third-party components above use licenses compatible with MaaNOP's `GPL-3.0-only`:

- MIT (MaaPracticeBoilerplate, MaaCommonAssets) — compatible.
- LGPL-3.0 (MaaFramework, maafw) — compatible; the library retains LGPL, the GPL-covered MaaNOP code may link it.
- Apache-2.0 (PaddleOCR, OpenCV) — compatible with GPL-3.0.
- PSF (CPython), MIT (ONNX Runtime, ViGEmClient, DirectML, .NET) — compatible.

No GPL-incompatible license (e.g. a use-restricting clause or a proprietary license) was identified among the distributed components.

If you believe any attribution above is inaccurate or incomplete, please open an issue at <https://github.com/ArcherSore/MaaNOP/issues>.
