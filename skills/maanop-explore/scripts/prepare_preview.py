"""Prepare a local preview and retain its controller-coordinate transform."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np


def prepare(source, output, controller_size, roi, short_side, max_encoded_bytes):
    source = Path(source).resolve()
    output = Path(output).resolve()
    metadata_path = output.with_suffix(output.suffix + ".json")
    if output == source or output.suffix.lower() not in (".jpg", ".jpeg"):
        raise ValueError("Use a separate .jpg/.jpeg output; never overwrite the source")
    if output.exists() or metadata_path.exists():
        raise ValueError("Output or metadata already exists; choose a new output name")
    if short_side <= 0 or max_encoded_bytes <= 0:
        raise ValueError("Short side and encoded-byte budget must be positive")
    source_bytes = source.read_bytes()
    image = cv2.imdecode(np.frombuffer(source_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Cannot decode source image")
    height, width = image.shape[:2]
    if list(controller_size) != [width, height]:
        raise ValueError("Source must be a full, unscaled controller screenshot of the declared size")
    x, y, w, h = roi if roi is not None else (0, 0, width, height)
    if w <= 0 or h <= 0:
        raise ValueError("ROI width and height must be positive")
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(width, x + w), min(height, y + h)
    if x1 <= x0 or y1 <= y0:
        raise ValueError("ROI does not intersect the source image")
    crop = image[y0:y1, x0:x1]
    crop_height, crop_width = crop.shape[:2]
    factor = min(1.0, short_side / min(crop_height, crop_width))
    out_width = max(1, round(crop_width * factor))
    out_height = max(1, round(crop_height * factor))
    prefix_bytes = len("data:image/jpeg;base64,")
    while True:
        preview = cv2.resize(crop, (out_width, out_height), interpolation=cv2.INTER_AREA)
        ok, encoded = cv2.imencode(".jpg", preview, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ok:
            raise ValueError("Cannot encode JPEG preview")
        encoded_bytes = 4 * ((len(encoded) + 2) // 3) + prefix_bytes
        if encoded_bytes <= max_encoded_bytes:
            break
        if out_width == out_height == 1:
            raise ValueError("Budget is smaller than the minimum JPEG data URL")
        out_width = max(1, math.floor(out_width * 0.8))
        out_height = max(1, math.floor(out_height * 0.8))
    metadata = {
        "source": str(source),
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "coordinate_system": "controller",
        "controller_size": [width, height],
        "requested_roi": list(roi) if roi is not None else None,
        "actual_roi": [x0, y0, crop_width, crop_height],
        "image_path": str(output),
        "image_size": [out_width, out_height],
        "image_to_controller": {
            "scale": [crop_width / out_width, crop_height / out_height],
            "offset": [x0, y0],
        },
        "file_bytes": len(encoded),
        "estimated_data_url_bytes": encoded_bytes,
        "max_encoded_bytes": max_encoded_bytes,
        "budget_scope": "JPEG base64 data URL only; excludes tool text, JSON wrapper and host re-encoding",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(encoded.tobytes())
    with metadata_path.open("x", encoding="utf-8") as stream:
        json.dump(metadata, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return {"image_path": str(output), "metadata_path": str(metadata_path), **metadata}


def map_point(metadata, point):
    width, height = metadata["image_size"]
    x, y = point
    if not (math.isfinite(x) and math.isfinite(y) and 0 <= x < width and 0 <= y < height):
        raise ValueError("Point must lie within the preview")
    sx, sy = metadata["image_to_controller"]["scale"]
    ox, oy = metadata["image_to_controller"]["offset"]
    mapped = [x * sx + ox, y * sy + oy]
    controller_width, controller_height = metadata["controller_size"]
    rounded = [round(mapped[0]), round(mapped[1])]
    if not (0 <= rounded[0] < controller_width and 0 <= rounded[1] < controller_height):
        raise ValueError("Rounded point is outside the controller; choose an interior point")
    crop_x, crop_y, crop_width, crop_height = metadata["actual_roi"]
    if not (crop_x <= rounded[0] < crop_x + crop_width and crop_y <= rounded[1] < crop_y + crop_height):
        raise ValueError("Rounded point is outside the crop; choose an interior point")
    return {"controller_point": mapped, "rounded_controller_point": rounded}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("prepare", help="Crop/resize a full controller image locally")
    make.add_argument("source", type=Path)
    make.add_argument("output", type=Path)
    make.add_argument("--controller-size", nargs=2, type=int, required=True, metavar=("W", "H"))
    make.add_argument("--roi", nargs=4, type=int, metavar=("X", "Y", "W", "H"))
    make.add_argument("--short-side", type=int, default=480)
    make.add_argument("--max-encoded-bytes", type=int, required=True)
    locate = commands.add_parser("map", help="Map one preview point; never sends a click")
    locate.add_argument("metadata", type=Path)
    locate.add_argument("x", type=float)
    locate.add_argument("y", type=float)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare(
                args.source, args.output, args.controller_size, args.roi,
                args.short_side, args.max_encoded_bytes,
            )
        else:
            result = map_point(json.loads(args.metadata.read_text(encoding="utf-8")), (args.x, args.y))
    except (OSError, ValueError, KeyError, TypeError, cv2.error) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
