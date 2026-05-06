# Setup and environment

This project can be used as a standalone Python CLI or installed as an image generation skill.

## API key

Live Gemini API calls require one of these environment variables:

- `GEMINI_API_KEY`
- `GOOGLE_API_KEY`

The Google Gen AI SDK automatically discovers either variable. If both are set, `GOOGLE_API_KEY` takes precedence.

For local development, `scripts/image_gen.py` also loads `./.env.txt` if neither variable is present in the current process. The file may contain either:

```text
GEMINI_API_KEY=your-key
```

or a single raw API key line.

Treat `.env.txt` as secret local state. Do not commit it.

## Dependencies

Install the Gemini SDK:

```bash
python -m pip install google-genai
```

Install Pillow if you want local downscaling or chroma-key post-processing:

```bash
python -m pip install pillow
```

`uv` users can install the same packages with:

```bash
uv pip install google-genai pillow
```

## Smoke test

Dry-run without network:

```bash
python scripts/image_gen.py generate \
  --prompt "A clean product-style image of a ceramic mug" \
  --aspect-ratio 1:1 \
  --out output/imagegen/dry-run.png \
  --dry-run
```

Live generation:

```bash
python scripts/image_gen.py generate \
  --prompt "A clean 3D illustration of a modern laptop on a desk, colorful abstract canvas on screen, no text, no logos" \
  --out output/imagegen/smoke-test.png
```

## Security

- Never commit API keys.
- Never print `.env.txt`.
- Prefer user or system environment variables for long-lived usage.
- Restrict Gemini API keys in Google Cloud where possible.
