# Gemini Image API quick reference

This file describes the Gemini / Nano Banana API surface used by `scripts/image_gen.py`.

## API key

Use `GEMINI_API_KEY` or `GOOGLE_API_KEY` as an environment variable. The Gemini SDK automatically discovers either variable; if both are set, `GOOGLE_API_KEY` takes precedence. For REST calls, send the key with the `x-goog-api-key` header.

The local CLI also loads `./.env.txt` as a convenience if neither variable is present. The file may contain either `GEMINI_API_KEY=...` or a single raw API key line. Do not print or commit that file.

## Models

| Model | Name | Use |
| --- | --- | --- |
| `gemini-3.1-flash-image-preview` | Nano Banana 2 | Default. Efficient image generation and editing for most project assets. |
| `gemini-3-pro-image-preview` | Nano Banana Pro | Professional assets, complex prompts, reasoning-heavy composition, and high-fidelity text. |
| `gemini-2.5-flash-image` | Nano Banana | Older low-latency image model. |

All generated images include SynthID watermarking.

## Endpoint

Gemini image generation and editing both use `generateContent`.

REST shape:

```bash
curl -s -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{
      "parts": [
        {"text": "Create a picture of a ceramic mug on a clean studio surface"}
      ]
    }]
  }'
```

Python SDK shape:

```python
from google import genai
from google.genai import types

client = genai.Client()
response = client.models.generate_content(
    model="gemini-3.1-flash-image-preview",
    contents=["Create a picture of a ceramic mug"],
    config=types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(
            aspect_ratio="16:9",
            image_size="2K",
        ),
    ),
)
for part in response.parts:
    if part.inline_data is not None:
        part.as_image().save("output.png")
```

## Text-to-image

Send a text prompt as `contents=[prompt]`.

`scripts/image_gen.py generate` maps to this pattern.

## Reference-image generation

Gemini accepts text plus one or more input images in `generateContent`. Use this when images are references for style, composition, subject direction, or visual mood.

`scripts/image_gen.py generate --reference-image ref.png --prompt "..."` maps to this pattern.

Be explicit about the role of the image:

```text
Use Image 1 only as a visual style reference.
Create a new product hero image with different objects and no copied text or logos.
```

## Text-and-image editing

Send a prompt plus one or more input images.

`scripts/image_gen.py edit --image input.png --prompt "..."` maps to this pattern.

For edits, state invariants explicitly:

```text
Change only the background to a warm sunset scene.
Keep the product, label text, edges, camera angle, and lighting on the product unchanged.
No extra text, logos, or watermark.
```

## Config used by the CLI

The CLI builds:

```json
{
  "responseModalities": ["TEXT", "IMAGE"],
  "imageConfig": {
    "aspectRatio": "16:9",
    "imageSize": "2K"
  }
}
```

`imageConfig` is omitted when neither `--aspect-ratio` nor `--image-size` is provided.

## Supported local CLI controls

- `--model`
- `--aspect-ratio`
- `--image-size`
- `--google-search`
- `--output-format`
- `--out`
- `--out-dir`
- `--n`
- `--downscale-max-dim`
- `--dry-run`

Controls such as `quality`, `background`, `input_fidelity`, and `moderation` are intentionally unsupported.

## Output handling

Gemini returns image data in response parts as inline data. The CLI extracts image bytes and writes them to local output paths. If text parts are returned, the CLI ignores them for file output; inspect the API response manually if you need model commentary.

## Limits and notes

- Large images and higher resolutions increase latency and cost.
- Inline input images should be kept small enough for Gemini API limits; the CLI warns above 20MB.
- `--n` makes repeated model calls because Gemini image responses are not a multi-image variant array.
- Use `generate-batch` for many different prompts.
- Gemini image generation does not expose a native transparent-background CLI control; use chroma-key prompting plus `scripts/remove_chroma_key.py`.
