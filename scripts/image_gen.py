#!/usr/bin/env python3
"""CLI for Gemini / Nano Banana image generation and editing.

The live path uses the Google Gen AI SDK (`google-genai`) and the Gemini API.
Dry-runs do not require the SDK, network access, or an API key.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import mimetypes
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

from io import BytesIO


DEFAULT_MODEL = "gemini-3.1-flash-image-preview"
DEFAULT_OUTPUT_FORMAT = "png"
DEFAULT_CONCURRENCY = 5
DEFAULT_DOWNSCALE_SUFFIX = "-web"
DEFAULT_OUTPUT_PATH = "output/imagegen/output.png"

GEMINI_IMAGE_MODELS = {
    "gemini-3.1-flash-image-preview",
    "gemini-3-pro-image-preview",
    "gemini-2.5-flash-image",
}
ALLOWED_ASPECT_RATIOS = {"1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"}
ALLOWED_IMAGE_SIZES = {"1K", "2K", "4K"}
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_BATCH_JOBS = 500


def _die(message: str, code: int = 1) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(code)


def _warn(message: str) -> None:
    print(f"Warning: {message}", file=sys.stderr)


def _dependency_hint(package: str, *, upgrade: bool = False) -> str:
    command = f"uv pip install {'-U ' if upgrade else ''}{package}"
    return (
        "Activate the repo-selected environment first, then install it with "
        f"`{command}`. If this repo uses a local virtualenv, start with "
        "`source .venv/bin/activate`; otherwise use this repo's configured shared fallback "
        "environment. If your project declares dependencies, prefer that project's normal "
        "`uv sync` flow."
    )


def _load_env_file_if_present() -> None:
    """Load GEMINI_API_KEY/GOOGLE_API_KEY from .env.txt for local runs.

    Environment variables still take precedence. This intentionally avoids
    printing values because API keys are secrets.
    """
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return

    candidates = [
        Path.cwd() / ".env.txt",
        Path(__file__).resolve().parents[1] / ".env.txt",
    ]
    for path in candidates:
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                os.environ["GEMINI_API_KEY"] = line
                return
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key in {"GEMINI_API_KEY", "GOOGLE_API_KEY"} and value:
                if not os.getenv(key):
                    os.environ[key] = value
        return


def _ensure_api_key(dry_run: bool) -> None:
    _load_env_file_if_present()
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        print("Gemini API key is set.", file=sys.stderr)
        return
    if dry_run:
        _warn("GEMINI_API_KEY or GOOGLE_API_KEY is not set; dry-run only.")
        return
    _die("GEMINI_API_KEY or GOOGLE_API_KEY is not set. Export it before running.")


def _read_prompt(prompt: Optional[str], prompt_file: Optional[str]) -> str:
    if prompt and prompt_file:
        _die("Use --prompt or --prompt-file, not both.")
    if prompt_file:
        path = Path(prompt_file)
        if not path.exists():
            _die(f"Prompt file not found: {path}")
        return path.read_text(encoding="utf-8").strip()
    if prompt:
        return prompt.strip()
    _die("Missing prompt. Use --prompt or --prompt-file.")
    return ""


def _check_image_paths(paths: Iterable[str]) -> List[Path]:
    resolved: List[Path] = []
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            _die(f"Image file not found: {path}")
        if path.stat().st_size > MAX_IMAGE_BYTES:
            _warn(f"Image exceeds 20MB; Gemini inline image input may reject it: {path}")
        resolved.append(path)
    return resolved


def _normalize_output_format(fmt: Optional[str]) -> str:
    if not fmt:
        return DEFAULT_OUTPUT_FORMAT
    fmt = fmt.lower()
    if fmt not in {"png", "jpeg", "jpg", "webp"}:
        _die("output-format must be png, jpeg, jpg, or webp.")
    return "jpeg" if fmt == "jpg" else fmt


def _build_output_paths(
    out: str,
    output_format: str,
    count: int,
    out_dir: Optional[str],
) -> List[Path]:
    ext = "." + output_format

    if out_dir:
        out_base = Path(out_dir)
        out_base.mkdir(parents=True, exist_ok=True)
        return [out_base / f"image_{i}{ext}" for i in range(1, count + 1)]

    out_path = Path(out)
    if out_path.exists() and out_path.is_dir():
        out_path.mkdir(parents=True, exist_ok=True)
        return [out_path / f"image_{i}{ext}" for i in range(1, count + 1)]

    if out_path.suffix == "":
        out_path = out_path.with_suffix(ext)
    elif out_path.suffix.lstrip(".").lower() != output_format:
        _warn(f"Output extension {out_path.suffix} does not match output-format {output_format}.")

    if count == 1:
        return [out_path]

    return [out_path.with_name(f"{out_path.stem}-{i}{out_path.suffix}") for i in range(1, count + 1)]


def _fields_from_args(args: argparse.Namespace) -> Dict[str, Optional[str]]:
    return {
        "use_case": getattr(args, "use_case", None),
        "asset_type": getattr(args, "asset_type", None),
        "scene": getattr(args, "scene", None),
        "subject": getattr(args, "subject", None),
        "style": getattr(args, "style", None),
        "composition": getattr(args, "composition", None),
        "lighting": getattr(args, "lighting", None),
        "palette": getattr(args, "palette", None),
        "materials": getattr(args, "materials", None),
        "text": getattr(args, "text", None),
        "constraints": getattr(args, "constraints", None),
        "negative": getattr(args, "negative", None),
    }


def _augment_prompt(args: argparse.Namespace, prompt: str) -> str:
    return _augment_prompt_fields(args.augment, prompt, _fields_from_args(args))


def _augment_prompt_fields(augment: bool, prompt: str, fields: Dict[str, Optional[str]]) -> str:
    if not augment:
        return prompt

    sections: List[str] = []
    if fields.get("use_case"):
        sections.append(f"Use case: {fields['use_case']}")
    if fields.get("asset_type"):
        sections.append(f"Asset type: {fields['asset_type']}")
    sections.append(f"Primary request: {prompt}")
    if fields.get("scene"):
        sections.append(f"Scene/backdrop: {fields['scene']}")
    if fields.get("subject"):
        sections.append(f"Subject: {fields['subject']}")
    if fields.get("style"):
        sections.append(f"Style/medium: {fields['style']}")
    if fields.get("composition"):
        sections.append(f"Composition/framing: {fields['composition']}")
    if fields.get("lighting"):
        sections.append(f"Lighting/mood: {fields['lighting']}")
    if fields.get("palette"):
        sections.append(f"Color palette: {fields['palette']}")
    if fields.get("materials"):
        sections.append(f"Materials/textures: {fields['materials']}")
    if fields.get("text"):
        sections.append(f"Text (verbatim): \"{fields['text']}\"")
    if fields.get("constraints"):
        sections.append(f"Constraints: {fields['constraints']}")
    if fields.get("negative"):
        sections.append(f"Avoid: {fields['negative']}")

    return "\n".join(sections)


def _validate_model(model: str) -> None:
    if not (model.startswith("gemini-") and "image" in model):
        _die(
            "model must be a Gemini image model, for example "
            "gemini-3.1-flash-image-preview or gemini-3-pro-image-preview."
        )


def _validate_aspect_ratio(aspect_ratio: Optional[str]) -> None:
    if aspect_ratio is not None and aspect_ratio not in ALLOWED_ASPECT_RATIOS:
        allowed = ", ".join(sorted(ALLOWED_ASPECT_RATIOS))
        _die(f"aspect-ratio must be one of: {allowed}.")


def _validate_image_size(image_size: Optional[str]) -> None:
    if image_size is not None and image_size not in ALLOWED_IMAGE_SIZES:
        allowed = ", ".join(sorted(ALLOWED_IMAGE_SIZES))
        _die(f"image-size must be one of: {allowed}.")


def _build_generation_config(args: argparse.Namespace) -> Dict[str, Any]:
    config: Dict[str, Any] = {"responseModalities": ["TEXT", "IMAGE"]}
    image_config: Dict[str, str] = {}
    if getattr(args, "aspect_ratio", None):
        image_config["aspectRatio"] = args.aspect_ratio
    if getattr(args, "image_size", None):
        image_config["imageSize"] = args.image_size
    if image_config:
        config["imageConfig"] = image_config
    return config


def _build_dry_run_payload(
    *,
    args: argparse.Namespace,
    prompt: str,
    outputs: List[Path],
    downscaled: Optional[List[str]],
    image_paths: Optional[List[Path]] = None,
) -> Dict[str, Any]:
    parts: List[Dict[str, Any]] = [{"text": prompt}]
    if image_paths:
        for path in image_paths:
            parts.append(
                {
                    "inlineData": {
                        "mimeType": _guess_mime_type(path),
                        "data": f"<base64:{path.name}>",
                    }
                }
            )

    payload: Dict[str, Any] = {
        "endpoint": f"models/{args.model}:generateContent",
        "model": args.model,
        "outputs": [str(p) for p in outputs],
        "outputs_downscaled": downscaled,
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": _build_generation_config(args),
    }
    if image_paths:
        payload["inputs"] = [str(p) for p in image_paths]
    if getattr(args, "google_search", False):
        payload["tools"] = [{"googleSearch": {}}]
    return payload


def _print_request(payload: dict) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _derive_downscale_path(path: Path, suffix: str) -> Path:
    if suffix and not suffix.startswith("-") and not suffix.startswith("_"):
        suffix = "-" + suffix
    return path.with_name(f"{path.stem}{suffix}{path.suffix}")


def _downscale_image_bytes(image_bytes: bytes, *, max_dim: int, output_format: str) -> bytes:
    try:
        from PIL import Image
    except Exception:
        _die(f"Downscaling requires Pillow. {_dependency_hint('pillow')}")

    if max_dim < 1:
        _die("--downscale-max-dim must be >= 1")

    with Image.open(BytesIO(image_bytes)) as img:
        img.load()
        w, h = img.size
        scale = min(1.0, float(max_dim) / float(max(w, h)))
        target = (max(1, int(round(w * scale))), max(1, int(round(h * scale))))
        resized = img if target == (w, h) else img.resize(target, Image.Resampling.LANCZOS)

        fmt = output_format.lower()
        if fmt == "jpg":
            fmt = "jpeg"
        if fmt == "jpeg":
            if resized.mode in ("RGBA", "LA") or ("transparency" in getattr(resized, "info", {})):
                bg = Image.new("RGB", resized.size, (255, 255, 255))
                rgba = resized.convert("RGBA")
                bg.paste(rgba, mask=rgba.split()[-1])
                resized = bg
            else:
                resized = resized.convert("RGB")

        out = BytesIO()
        resized.save(out, format=fmt.upper())
        return out.getvalue()


def _write_images(
    images: List[bytes],
    outputs: List[Path],
    *,
    force: bool,
    downscale_max_dim: Optional[int],
    downscale_suffix: str,
    output_format: str,
) -> None:
    if not images:
        _die("Gemini response did not contain image data.")

    for idx, image_bytes in enumerate(images):
        if idx >= len(outputs):
            break
        out_path = outputs[idx]
        if out_path.exists() and not force:
            _die(f"Output already exists: {out_path} (use --force to overwrite)")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(image_bytes)
        print(f"Wrote {out_path}")

        if downscale_max_dim is None:
            continue

        derived = _derive_downscale_path(out_path, downscale_suffix)
        if derived.exists() and not force:
            _die(f"Output already exists: {derived} (use --force to overwrite)")
        derived.parent.mkdir(parents=True, exist_ok=True)
        resized = _downscale_image_bytes(image_bytes, max_dim=downscale_max_dim, output_format=output_format)
        derived.write_bytes(resized)
        print(f"Wrote {derived}")


def _create_client():
    try:
        from google import genai
    except ImportError:
        _die(f"google-genai SDK not installed in the active environment. {_dependency_hint('google-genai')}")
    return genai.Client()


def _create_types_module():
    try:
        from google.genai import types
    except ImportError:
        _die(f"google-genai SDK not installed in the active environment. {_dependency_hint('google-genai')}")
    return types


def _guess_mime_type(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "image/png"


def _read_image_part(path: Path) -> Any:
    types = _create_types_module()
    return types.Part.from_bytes(data=path.read_bytes(), mime_type=_guess_mime_type(path))


def _response_images(response: Any) -> List[bytes]:
    images: List[bytes] = []
    parts = getattr(response, "parts", None)
    if parts is None:
        candidates = getattr(response, "candidates", []) or []
        if candidates:
            content = getattr(candidates[0], "content", None)
            parts = getattr(content, "parts", None)
    for part in parts or []:
        inline_data = getattr(part, "inline_data", None) or getattr(part, "inlineData", None)
        if inline_data is None and isinstance(part, dict):
            inline_data = part.get("inline_data") or part.get("inlineData")
        if inline_data is not None:
            data = getattr(inline_data, "data", None)
            if data is None and isinstance(inline_data, dict):
                data = inline_data.get("data")
            if isinstance(data, str):
                images.append(base64.b64decode(data))
                continue
            if isinstance(data, bytes):
                images.append(data)
                continue

        as_image = getattr(part, "as_image", None)
        if not callable(as_image):
            continue
        try:
            image = as_image()
        except Exception:
            continue
        if image is None:
            continue
        if hasattr(image, "data") and isinstance(image.data, (bytes, bytearray)):
            images.append(bytes(image.data))
            continue
        out = BytesIO()
        try:
            image.save(out, format="PNG")
        except TypeError:
            image.save(out)
        images.append(out.getvalue())
    return images


def _sdk_generation_config(args: argparse.Namespace) -> Any:
    types = _create_types_module()
    image_config = None
    if getattr(args, "aspect_ratio", None) or getattr(args, "image_size", None):
        image_config = types.ImageConfig(
            aspect_ratio=getattr(args, "aspect_ratio", None),
            image_size=getattr(args, "image_size", None),
        )

    tools = None
    if getattr(args, "google_search", False):
        tools = [{"google_search": {}}]

    return types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=image_config,
        tools=tools,
    )


def _call_generate_content(client: Any, args: argparse.Namespace, contents: List[Any]) -> Any:
    return client.models.generate_content(
        model=args.model,
        contents=contents,
        config=_sdk_generation_config(args),
    )


def _run_generate_request(args: argparse.Namespace, prompt: str) -> List[bytes]:
    client = _create_client()
    response = _call_generate_content(client, args, [prompt])
    return _response_images(response)


def _run_generate_request_with_retries(
    args: argparse.Namespace,
    prompt: str,
    *,
    attempts: int,
) -> List[bytes]:
    last_exc: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            return _run_generate_request(args, prompt)
        except Exception as exc:
            last_exc = exc
            if not _is_transient_error(exc) or attempt == attempts:
                raise
            sleep_s = _extract_retry_after_seconds(exc)
            if sleep_s is None:
                sleep_s = min(60.0, 2.0**attempt)
            print(
                f"Generation attempt {attempt}/{attempts} failed ({exc.__class__.__name__}); retrying in {sleep_s:.1f}s",
                file=sys.stderr,
            )
            time.sleep(sleep_s)
    raise last_exc or RuntimeError("unknown error")


def _run_edit_request(args: argparse.Namespace, prompt: str, image_paths: List[Path]) -> List[bytes]:
    contents: List[Any] = [prompt]
    contents.extend(_read_image_part(path) for path in image_paths)
    client = _create_client()
    response = _call_generate_content(client, args, contents)
    return _response_images(response)


def _run_edit_request_with_retries(
    args: argparse.Namespace,
    prompt: str,
    image_paths: List[Path],
    *,
    attempts: int,
) -> List[bytes]:
    last_exc: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            return _run_edit_request(args, prompt, image_paths)
        except Exception as exc:
            last_exc = exc
            if not _is_transient_error(exc) or attempt == attempts:
                raise
            sleep_s = _extract_retry_after_seconds(exc)
            if sleep_s is None:
                sleep_s = min(60.0, 2.0**attempt)
            print(
                f"Edit attempt {attempt}/{attempts} failed ({exc.__class__.__name__}); retrying in {sleep_s:.1f}s",
                file=sys.stderr,
            )
            time.sleep(sleep_s)
    raise last_exc or RuntimeError("unknown error")


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value[:60] if value else "job"


def _normalize_job(job: Any, idx: int) -> Dict[str, Any]:
    if isinstance(job, str):
        prompt = job.strip()
        if not prompt:
            _die(f"Empty prompt at job {idx}")
        return {"prompt": prompt}
    if isinstance(job, dict):
        if "prompt" not in job or not str(job["prompt"]).strip():
            _die(f"Missing prompt for job {idx}")
        return job
    _die(f"Invalid job at index {idx}: expected string or object.")
    return {}


def _read_jobs_jsonl(path: str) -> List[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        _die(f"Input file not found: {p}")
    jobs: List[Dict[str, Any]] = []
    for line_no, raw in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            item: Any = json.loads(line) if line.startswith("{") else line
            jobs.append(_normalize_job(item, idx=line_no))
        except json.JSONDecodeError as exc:
            _die(f"Invalid JSON on line {line_no}: {exc}")
    if not jobs:
        _die("No jobs found in input file.")
    if len(jobs) > MAX_BATCH_JOBS:
        _die(f"Too many jobs ({len(jobs)}). Max is {MAX_BATCH_JOBS}.")
    return jobs


def _merge_non_null(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(dst)
    for k, v in src.items():
        if v is not None:
            merged[k] = v
    return merged


def _job_output_paths(
    *,
    out_dir: Path,
    output_format: str,
    idx: int,
    prompt: str,
    n: int,
    explicit_out: Optional[str],
) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = "." + output_format
    if explicit_out:
        base = Path(explicit_out)
        if base.suffix == "":
            base = base.with_suffix(ext)
        elif base.suffix.lstrip(".").lower() != output_format:
            _warn(f"Job {idx}: output extension {base.suffix} does not match output-format {output_format}.")
        base = out_dir / base.name
    else:
        slug = _slugify(prompt[:80])
        base = out_dir / f"{idx:03d}-{slug}{ext}"

    if n == 1:
        return [base]
    return [base.with_name(f"{base.stem}-{i}{base.suffix}") for i in range(1, n + 1)]


def _extract_retry_after_seconds(exc: Exception) -> Optional[float]:
    for attr in ("retry_after", "retry_after_seconds"):
        val = getattr(exc, attr, None)
        if isinstance(val, (int, float)) and val >= 0:
            return float(val)
    msg = str(exc)
    m = re.search(r"retry[- ]after[:= ]+([0-9]+(?:\.[0-9]+)?)", msg, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            return None
    return None


def _is_transient_error(exc: Exception) -> bool:
    name = exc.__class__.__name__.lower()
    msg = str(exc).lower()
    return (
        "rate" in name
        or "timeout" in name
        or "tempor" in name
        or "429" in msg
        or "rate limit" in msg
        or "timeout" in msg
        or "temporar" in msg
        or "connection reset" in msg
    )


async def _generate_one_with_retries(
    args: argparse.Namespace,
    prompt: str,
    *,
    attempts: int,
    job_label: str,
) -> List[bytes]:
    last_exc: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            return await asyncio.to_thread(_run_generate_request, args, prompt)
        except Exception as exc:
            last_exc = exc
            if not _is_transient_error(exc) or attempt == attempts:
                raise
            sleep_s = _extract_retry_after_seconds(exc)
            if sleep_s is None:
                sleep_s = min(60.0, 2.0**attempt)
            print(
                f"{job_label} attempt {attempt}/{attempts} failed ({exc.__class__.__name__}); retrying in {sleep_s:.1f}s",
                file=sys.stderr,
            )
            await asyncio.sleep(sleep_s)
    raise last_exc or RuntimeError("unknown error")


def _args_copy_with_overrides(args: argparse.Namespace, overrides: Dict[str, Any]) -> argparse.Namespace:
    values = vars(args).copy()
    values.update({k: v for k, v in overrides.items() if v is not None})
    return argparse.Namespace(**values)


async def _run_generate_batch(args: argparse.Namespace) -> int:
    jobs = _read_jobs_jsonl(args.input)
    out_dir = Path(args.out_dir)
    output_format = _normalize_output_format(args.output_format)
    base_fields = _fields_from_args(args)

    if args.dry_run:
        for i, job in enumerate(jobs, start=1):
            prompt = str(job["prompt"]).strip()
            fields = _merge_non_null(base_fields, job.get("fields", {}))
            fields = _merge_non_null(fields, {k: job.get(k) for k in base_fields.keys()})
            augmented = _augment_prompt_fields(args.augment, prompt, fields)
            job_args = _args_copy_with_overrides(
                args,
                {k: job.get(k) for k in ("model", "aspect_ratio", "image_size", "google_search", "output_format", "n")},
            )
            job_output_format = _normalize_output_format(getattr(job_args, "output_format", output_format))
            n = int(getattr(job_args, "n", 1))
            outputs = _job_output_paths(
                out_dir=out_dir,
                output_format=job_output_format,
                idx=i,
                prompt=prompt,
                n=n,
                explicit_out=job.get("out"),
            )
            downscaled = None
            if args.downscale_max_dim is not None:
                downscaled = [str(_derive_downscale_path(p, args.downscale_suffix)) for p in outputs]
            _print_request(_build_dry_run_payload(args=job_args, prompt=augmented, outputs=outputs, downscaled=downscaled))
        return 0

    sem = asyncio.Semaphore(args.concurrency)
    any_failed = False

    async def run_job(i: int, job: Dict[str, Any]) -> Tuple[int, Optional[str]]:
        nonlocal any_failed
        prompt = str(job["prompt"]).strip()
        job_label = f"[job {i}/{len(jobs)}]"
        fields = _merge_non_null(base_fields, job.get("fields", {}))
        fields = _merge_non_null(fields, {k: job.get(k) for k in base_fields.keys()})
        augmented = _augment_prompt_fields(args.augment, prompt, fields)
        job_args = _args_copy_with_overrides(
            args,
            {k: job.get(k) for k in ("model", "aspect_ratio", "image_size", "google_search", "output_format", "n")},
        )
        job_output_format = _normalize_output_format(getattr(job_args, "output_format", output_format))
        n = int(getattr(job_args, "n", 1))
        outputs = _job_output_paths(
            out_dir=out_dir,
            output_format=job_output_format,
            idx=i,
            prompt=prompt,
            n=n,
            explicit_out=job.get("out"),
        )
        try:
            async with sem:
                print(f"{job_label} starting", file=sys.stderr)
                started = time.time()
                images = await _generate_one_with_retries(
                    job_args,
                    augmented,
                    attempts=args.max_attempts,
                    job_label=job_label,
                )
                elapsed = time.time() - started
                print(f"{job_label} completed in {elapsed:.1f}s", file=sys.stderr)
            _write_images(
                images,
                outputs,
                force=args.force,
                downscale_max_dim=args.downscale_max_dim,
                downscale_suffix=args.downscale_suffix,
                output_format=job_output_format,
            )
            return i, None
        except Exception as exc:
            any_failed = True
            print(f"{job_label} failed: {exc}", file=sys.stderr)
            if args.fail_fast:
                raise
            return i, str(exc)

    tasks = [asyncio.create_task(run_job(i, job)) for i, job in enumerate(jobs, start=1)]
    try:
        await asyncio.gather(*tasks)
    except Exception:
        for task in tasks:
            if not task.done():
                task.cancel()
        raise
    return 1 if any_failed else 0


def _generate_batch(args: argparse.Namespace) -> None:
    exit_code = asyncio.run(_run_generate_batch(args))
    if exit_code:
        raise SystemExit(exit_code)


def _generate(args: argparse.Namespace) -> None:
    prompt = _augment_prompt(args, _read_prompt(args.prompt, args.prompt_file))
    output_format = _normalize_output_format(args.output_format)
    output_paths = _build_output_paths(args.out, output_format, args.n, args.out_dir)
    downscaled = None
    if args.downscale_max_dim is not None:
        downscaled = [str(_derive_downscale_path(p, args.downscale_suffix)) for p in output_paths]

    if args.dry_run:
        _print_request(_build_dry_run_payload(args=args, prompt=prompt, outputs=output_paths, downscaled=downscaled))
        return

    print("Calling Gemini API (generation). This can take up to a couple of minutes.", file=sys.stderr)
    started = time.time()
    images: List[bytes] = []
    for idx in range(args.n):
        if args.n > 1:
            print(f"Variant {idx + 1}/{args.n}", file=sys.stderr)
        images.extend(_run_generate_request_with_retries(args, prompt, attempts=args.max_attempts))
    elapsed = time.time() - started
    print(f"Generation completed in {elapsed:.1f}s.", file=sys.stderr)
    _write_images(
        images,
        output_paths,
        force=args.force,
        downscale_max_dim=args.downscale_max_dim,
        downscale_suffix=args.downscale_suffix,
        output_format=output_format,
    )


def _edit(args: argparse.Namespace) -> None:
    prompt = _augment_prompt(args, _read_prompt(args.prompt, args.prompt_file))
    image_paths = _check_image_paths(args.image)
    output_format = _normalize_output_format(args.output_format)
    output_paths = _build_output_paths(args.out, output_format, args.n, args.out_dir)
    downscaled = None
    if args.downscale_max_dim is not None:
        downscaled = [str(_derive_downscale_path(p, args.downscale_suffix)) for p in output_paths]

    if args.dry_run:
        _print_request(
            _build_dry_run_payload(
                args=args,
                prompt=prompt,
                outputs=output_paths,
                downscaled=downscaled,
                image_paths=image_paths,
            )
        )
        return

    print(f"Calling Gemini API (edit) with {len(image_paths)} image(s).", file=sys.stderr)
    started = time.time()
    images: List[bytes] = []
    for idx in range(args.n):
        if args.n > 1:
            print(f"Variant {idx + 1}/{args.n}", file=sys.stderr)
        images.extend(
            _run_edit_request_with_retries(
                args,
                prompt,
                image_paths,
                attempts=args.max_attempts,
            )
        )
    elapsed = time.time() - started
    print(f"Edit completed in {elapsed:.1f}s.", file=sys.stderr)
    _write_images(
        images,
        output_paths,
        force=args.force,
        downscale_max_dim=args.downscale_max_dim,
        downscale_suffix=args.downscale_suffix,
        output_format=output_format,
    )


def _add_shared_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--prompt")
    parser.add_argument("--prompt-file")
    parser.add_argument("--n", type=int, default=1)
    parser.add_argument("--aspect-ratio")
    parser.add_argument("--image-size")
    parser.add_argument("--google-search", action="store_true")
    parser.add_argument("--output-format")
    parser.add_argument("--out", default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--out-dir")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--augment", dest="augment", action="store_true")
    parser.add_argument("--no-augment", dest="augment", action="store_false")
    parser.set_defaults(augment=True)

    parser.add_argument("--use-case")
    parser.add_argument("--asset-type")
    parser.add_argument("--scene")
    parser.add_argument("--subject")
    parser.add_argument("--style")
    parser.add_argument("--composition")
    parser.add_argument("--lighting")
    parser.add_argument("--palette")
    parser.add_argument("--materials")
    parser.add_argument("--text")
    parser.add_argument("--constraints")
    parser.add_argument("--negative")

    parser.add_argument("--downscale-max-dim", type=int)
    parser.add_argument("--downscale-suffix", default=DEFAULT_DOWNSCALE_SUFFIX)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CLI for Gemini / Nano Banana image generation and editing"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen_parser = subparsers.add_parser("generate", help="Create a new image")
    _add_shared_args(gen_parser)
    gen_parser.set_defaults(func=_generate)

    batch_parser = subparsers.add_parser(
        "generate-batch",
        help="Generate multiple prompts concurrently (JSONL input)",
    )
    _add_shared_args(batch_parser)
    batch_parser.add_argument("--input", required=True, help="Path to JSONL file (one job per line)")
    batch_parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    batch_parser.add_argument("--fail-fast", action="store_true")
    batch_parser.set_defaults(func=_generate_batch)

    edit_parser = subparsers.add_parser("edit", help="Edit an existing image")
    _add_shared_args(edit_parser)
    edit_parser.add_argument("--image", action="append", required=True)
    edit_parser.set_defaults(func=_edit)

    args = parser.parse_args()
    if args.n < 1 or args.n > 10:
        _die("--n must be between 1 and 10")
    if getattr(args, "concurrency", 1) < 1 or getattr(args, "concurrency", 1) > 25:
        _die("--concurrency must be between 1 and 25")
    if getattr(args, "max_attempts", 3) < 1 or getattr(args, "max_attempts", 3) > 10:
        _die("--max-attempts must be between 1 and 10")
    if getattr(args, "downscale_max_dim", None) is not None and args.downscale_max_dim < 1:
        _die("--downscale-max-dim must be >= 1")
    if args.command == "generate-batch" and not args.out_dir:
        _die("generate-batch requires --out-dir")

    _validate_model(args.model)
    _validate_aspect_ratio(args.aspect_ratio)
    _validate_image_size(args.image_size)
    _ensure_api_key(args.dry_run)

    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
