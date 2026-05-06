# Gemini ImageGen

[繁體中文](README.md) | **English**

Gemini ImageGen is a small Gemini / Nano Banana image generation skill and Python CLI. It can generate new raster images, edit existing images with text-and-image prompts, run prompt batches, and create chroma-key sources for transparent-background assets.

The project is intentionally usable in two ways:

- As a standalone CLI through `scripts/image_gen.py`.
- As a skill package through `SKILL.md` and `agents/gemini.yaml`.

## Features

- Text-to-image generation with Gemini image models.
- Text-and-image editing with one or more input images.
- JSONL batch generation.
- Prompt augmentation fields for common asset workflows.
- Local output management with non-destructive defaults.
- Optional downscaled web copies.
- Chroma-key workflow for transparent-background cutouts.

## Requirements

- Python 3.10 or newer.
- A Gemini API key.
- `google-genai`.
- `pillow` for downscaling and chroma-key post-processing.

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

## Transparent Cutouts

For simple opaque subjects, generate the subject on a flat chroma-key background:

```bash
python scripts/image_gen.py generate \
  --prompt "A reusable water bottle centered on a perfectly flat solid #00ff00 background for local background removal; no shadows, gradients, texture, floor plane, reflection, text, or logos" \
  --out tmp/imagegen/bottle-source.png
```

Then remove the key color:

```bash
python scripts/remove_chroma_key.py \
  --input tmp/imagegen/bottle-source.png \
  --out output/imagegen/bottle-cutout.png \
  --auto-key border \
  --soft-matte \
  --transparent-threshold 12 \
  --opaque-threshold 220 \
  --despill
```

## Project Layout

- `SKILL.md`: skill instructions.
- `agents/gemini.yaml`: skill metadata.
- `scripts/image_gen.py`: Gemini image CLI.
- `scripts/remove_chroma_key.py`: local chroma-key removal helper.
- `references/`: usage, environment, and prompting notes.
- `tests/`: CLI behavior tests.

## Validation

Run:

```bash
python -B -m unittest tests.test_image_gen -v
```

## License

See `LICENSE.txt`.
