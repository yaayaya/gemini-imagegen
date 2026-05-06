# CLI reference (`scripts/image_gen.py`)

This CLI uses Gemini / Nano Banana image models through the Google Gen AI SDK.

Real API calls require network access and `GEMINI_API_KEY` or `GOOGLE_API_KEY`. `--dry-run` does not.

## Dependencies

Install the SDK in the active environment:

```bash
uv pip install google-genai
```

Optional post-processing dependencies:

```bash
uv pip install pillow
```

Pillow is needed for downscaling and local chroma-key post-processing.

## API key

Preferred:

```bash
export GEMINI_API_KEY="<your key>"
```

Windows PowerShell:

```powershell
$env:GEMINI_API_KEY = "<your key>"
```

The CLI also loads `./.env.txt` as a local convenience if neither `GEMINI_API_KEY` nor `GOOGLE_API_KEY` is set. It accepts either `GEMINI_API_KEY=...` or a single raw API key line. Keep that file private.

## Dry-run

```bash
python scripts/image_gen.py generate \
  --prompt "A minimal product photo of a ceramic mug" \
  --aspect-ratio 16:9 \
  --image-size 2K \
  --out output/imagegen/mug.png \
  --dry-run
```

Dry-runs print the request shape and computed output paths.

## Generate

```bash
python scripts/image_gen.py generate \
  --prompt "A cozy alpine cabin at dawn, photorealistic, warm window light" \
  --aspect-ratio 16:9 \
  --image-size 2K \
  --out output/imagegen/alpine-cabin.png
```

## Edit

```bash
python scripts/image_gen.py edit \
  --image input.png \
  --prompt "Replace only the background with a warm sunset scene; keep the product unchanged" \
  --aspect-ratio 1:1 \
  --out output/imagegen/sunset-edit.png
```

Pass repeated `--image` flags for multiple inputs. Describe each image role in the prompt.

## Batch generation

```bash
mkdir -p tmp/imagegen output/imagegen/batch
cat > tmp/imagegen/prompts.jsonl << 'EOF'
{"prompt":"Cavernous hangar interior with a compact shuttle parked near the center","use_case":"stylized-concept","composition":"wide-angle, low-angle","lighting":"volumetric light rays","aspect_ratio":"16:9","out":"hangar.png"}
{"prompt":"A matte ceramic mug on a stone counter","use_case":"product-mockup","composition":"clean studio product photo","aspect_ratio":"1:1","out":"mug.png"}
EOF

python scripts/image_gen.py generate-batch \
  --input tmp/imagegen/prompts.jsonl \
  --out-dir output/imagegen/batch \
  --concurrency 5
```

Notes:
- `generate-batch` requires `--out-dir`.
- Per-job overrides support `model`, `aspect_ratio`, `image_size`, `google_search`, `output_format`, `n`, `out`, and prompt augmentation fields.
- `--n` creates repeated variants by making repeated model calls.

## Models

Default:

```bash
--model gemini-3.1-flash-image-preview
```

High-fidelity / complex:

```bash
--model gemini-3-pro-image-preview
```

Older low-latency:

```bash
--model gemini-2.5-flash-image
```

## Aspect ratio and size

Common ratios:

```text
1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3, 4:5, 5:4, 21:9
```

Image sizes:

```text
1K, 2K, 4K
```

Not every model or account tier may support every combination. If a live request fails, rerun with fewer explicit controls or choose the Pro image model for complex output.

## Search grounding

Use `--google-search` when the image should reflect current or factual context and the selected model/tool path supports Google Search grounding:

```bash
python scripts/image_gen.py generate \
  --prompt "Use current search context to create an editorial magazine page about Gemini image models" \
  --google-search \
  --model gemini-3.1-flash-image-preview \
  --out output/imagegen/editorial.png
```

## Output handling

- Use `tmp/imagegen/` for scratch prompt files or intermediate chroma-key sources.
- Use `output/imagegen/` for final outputs.
- Reruns fail if the target exists unless `--force` is set.
- `--downscale-max-dim` writes an additional smaller copy with suffix `-web` by default.

## Unsupported controls

Do not use:

- `--quality`
- `--background`
- `--input-fidelity`
- `--moderation`
- non-Gemini image model names

Gemini controls image generation through `generateContent`, prompt instructions, and optional `imageConfig`.
