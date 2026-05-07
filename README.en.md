# Gemini ImageGen

[繁體中文](README.md) | **English**

Gemini ImageGen is a small Gemini / Nano Banana image generation skill and Python CLI. It can generate new raster images, edit existing images with text-and-image prompts, and run prompt batches.

The project is intentionally usable in two ways:

- As a standalone CLI through `scripts/image_gen.py`.
- As a skill package through `SKILL.md` and `agents/gemini.yaml`.

## Features

- Text-to-image generation with Gemini image models.
- Reference-image guided generation for style, composition, or visual direction.
- Text-and-image editing with one or more input images.
- JSONL batch generation.
- Prompt augmentation fields for common asset workflows.
- Local output management with non-destructive defaults.
- Optional downscaled web copies.

## Requirements

- Python 3.10 or newer.
- A Gemini API key.
- `google-genai`.
- `pillow` for optional downscaled web copies.

Install dependencies:

```bash
python -m pip install google-genai pillow
```

## API Key

Set one of these environment variables:

```bash
export GEMINI_API_KEY="your-key"
```

PowerShell:

```powershell
$env:GEMINI_API_KEY = "your-key"
```

The CLI also supports a local `.env.txt` file for development. It may contain either:

```text
GEMINI_API_KEY=your-key
```

or a single raw API key line.

Do not commit `.env.txt`.

## Quick Start

Dry-run the request without using network or credits:

```bash
python scripts/image_gen.py generate \
  --prompt "A clean product-style image of a ceramic mug" \
  --aspect-ratio 1:1 \
  --out output/imagegen/mug.png \
  --dry-run
```

Generate an image:

```bash
python scripts/image_gen.py generate \
  --prompt "A clean 3D illustration of a modern laptop on a desk, colorful abstract canvas on screen, no text, no logos" \
  --out output/imagegen/workspace.png
```

Generate a new image from a reference image:

```bash
python scripts/image_gen.py generate \
  --reference-image input/style-reference.png \
  --prompt "Create a new landing page hero image using the reference image only for visual style; do not copy any text or logo" \
  --out output/imagegen/hero-from-reference.png
```

Edit an image:

```bash
python scripts/image_gen.py edit \
  --image input/product.png \
  --prompt "Replace only the background with a warm sunset gradient; keep the product, label text, edges, and camera angle unchanged" \
  --out output/imagegen/product-sunset.png
```

## Models

Default:

```text
gemini-3.1-flash-image-preview
```

Other useful options:

```text
gemini-3-pro-image-preview
gemini-2.5-flash-image
```

Use `--model` to choose a model:

```bash
python scripts/image_gen.py generate \
  --model gemini-3-pro-image-preview \
  --prompt "A premium editorial product image of a ceramic mug" \
  --out output/imagegen/mug-premium.png
```

## Batch Generation

Create `tmp/imagegen/prompts.jsonl`:

```jsonl
{"prompt":"A tactile 3D app icon for a habit tracker, no text","use_case":"logo-brand","aspect_ratio":"1:1","out":"habit-icon.png"}
{"prompt":"A cozy reading nook at dusk, editorial photography","use_case":"photorealistic-natural","aspect_ratio":"4:3","out":"reading-nook.png"}
```

Run:

```bash
python scripts/image_gen.py generate-batch \
  --input tmp/imagegen/prompts.jsonl \
  --out-dir output/imagegen/batch \
  --concurrency 5
```

## Transparent Backgrounds

Transparent-background output is not supported. Gemini ImageGen focuses on generating and editing regular raster images. For high-quality transparent backgrounds, use a dedicated background-removal tool or a manual image editing workflow.

## Project Layout

- `SKILL.md`: skill instructions.
- `agents/gemini.yaml`: skill metadata.
- `scripts/image_gen.py`: Gemini image CLI.
- `references/`: usage, environment, and prompting notes.
- `tests/`: CLI behavior tests.

## Validation

Run:

```bash
python -B -m unittest tests.test_image_gen -v
```

## License

See `LICENSE.txt`.
