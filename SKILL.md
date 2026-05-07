---
name: "gemini-imagegen"
description: "Generate or edit raster images with Gemini / Nano Banana when a project needs bitmap visuals such as photos, illustrations, textures, sprites, mockups, product images, transparent-background cutouts, or visual variants. Use when Codex should create a new bitmap asset, transform an existing image, or derive variants from references. Do not use when deterministic SVG/vector/code-native output is a better fit."
---

# Gemini Image Generation Skill

Generates or edits project images through the Gemini API's native image models, also known as Nano Banana.

## Top-level mode

Use **Gemini CLI mode** by default:

```bash
python scripts/image_gen.py generate --prompt "..." --out output/imagegen/result.png
python scripts/image_gen.py edit --image input.png --prompt "..." --out output/imagegen/edit.png
python scripts/image_gen.py generate-batch --input tmp/imagegen/prompts.jsonl --out-dir output/imagegen/batch
```

Live API calls require `GEMINI_API_KEY` or `GOOGLE_API_KEY`. The SDK automatically picks up either variable, with `GOOGLE_API_KEY` taking precedence when both exist. This repo's CLI also loads `./.env.txt` as a local convenience if neither variable is present in the process environment; `.env.txt` may contain either `GEMINI_API_KEY=...` or a single raw API key line. Never print or commit API keys.

Use `--dry-run` to inspect the request shape without network access, the SDK, or an API key.

## Models

Default model:
- `gemini-3.1-flash-image-preview`: Nano Banana 2, optimized for efficient high-volume image generation and editing.

Alternate models:
- `gemini-3-pro-image-preview`: Nano Banana Pro, better for professional assets, complex instructions, and high-fidelity text.
- `gemini-2.5-flash-image`: Nano Banana, older low-latency option.

All generated images include Google's SynthID watermark.

## When to use

- Generate a new image: concept art, product shot, cover, website hero, texture, sprite, icon-like bitmap, UI mockup, or infographic.
- Generate a new image with one or more reference images for style, composition, subject direction, or visual mood using `generate --reference-image`.
- Edit an existing image: object removal/replacement, background change, style transfer, lighting/weather changes, compositing, or transparent-background preparation.
- Create many assets or variants for a project.

## When not to use

- Extending existing SVG/vector icon systems.
- Creating simple deterministic diagrams or UI primitives that are better authored in SVG, HTML/CSS, canvas, or native code.
- Editing a small project-local asset when the source is already available in a native editable format.

## Workflow

1. Decide intent: `generate` for new images, `generate --reference-image` when input images are references, and `edit` when preserving or transforming an existing image.
2. Decide whether the output is preview-only or project-bound.
3. Collect prompt, exact text, constraints, avoid list, output path, and image inputs.
4. Label every input image by role: edit target, style reference, composition reference, or compositing source.
5. Shape the prompt using `references/prompting.md`.
6. Run `scripts/image_gen.py` with `--dry-run` first when using API/model controls or batch jobs.
7. Run the live command after confirming the request shape and API key availability.
8. Inspect the generated output for subject, style, composition, text accuracy, and invariants.
9. Iterate with one targeted change at a time.
10. Save project-bound final assets under the workspace, usually `output/imagegen/` or the consuming app's asset folder.
11. Never overwrite an existing asset unless the user explicitly asked for replacement; otherwise use a versioned filename.
12. Report final saved paths, model, and final prompt.

## CLI controls

Shared:
- `--model`: defaults to `gemini-3.1-flash-image-preview`.
- `--aspect-ratio`: common ratios include `1:1`, `16:9`, `9:16`, `4:3`, `3:4`, `3:2`, `2:3`, `4:5`, `5:4`, `21:9`.
- `--image-size`: `1K`, `2K`, or `4K`.
- `--google-search`: enables Google Search grounding for models/tool paths that support it.
- `--output-format`: `png`, `jpeg`, or `webp`; this controls the local saved file format when post-processing is available.
- `--n`: generates repeated variants by making repeated model calls.
- `--downscale-max-dim`: also writes a smaller web copy.

Unsupported controls:
- Do not use `quality`, `background`, `input_fidelity`, or `moderation`. They are not Gemini image CLI arguments.

## Transparent image requests

Gemini image generation does not expose a universal local CLI flag for native transparent output. Use a chroma-key workflow for simple opaque subjects:

1. Prompt Gemini to generate the subject on a perfectly flat solid chroma-key background.
2. Default key color is `#00ff00`; use `#ff00ff` for green subjects.
3. Require no shadows, gradients, texture, reflections, floor plane, or lighting variation in the background.
4. Copy the generated source into the workspace or `tmp/imagegen/`.
5. Run `scripts/remove_chroma_key.py`:

```bash
python scripts/remove_chroma_key.py \
  --input tmp/imagegen/source.png \
  --out output/imagegen/cutout.png \
  --auto-key border \
  --soft-matte \
  --transparent-threshold 12 \
  --opaque-threshold 220 \
  --despill
```

If the request involves hair, glass, smoke, liquids, translucent materials, reflective objects, soft shadows, or key-color conflicts, explain that chroma-key removal may need iteration or manual cleanup.

Prompt transparent requests like this:

```text
Create the requested subject on a perfectly flat solid #00ff00 chroma-key background for background removal.
The background must be one uniform color with no shadows, gradients, texture, reflections, floor plane, or lighting variation.
Keep the subject fully separated from the background with crisp edges and generous padding.
Do not use #00ff00 anywhere in the subject.
No cast shadow, no contact shadow, no reflection, no watermark, and no text unless explicitly requested.
```

## Use-case taxonomy

Generate:
- `photorealistic-natural`
- `product-mockup`
- `ui-mockup`
- `infographic-diagram`
- `scientific-educational`
- `ads-marketing`
- `productivity-visual`
- `logo-brand`
- `illustration-story`
- `stylized-concept`
- `historical-scene`

Edit:
- `text-localization`
- `identity-preserve`
- `precise-object-edit`
- `lighting-weather`
- `background-extraction`
- `style-transfer`
- `compositing`
- `sketch-to-render`

## Shared prompt schema

Use only the lines that help:

```text
Use case: <taxonomy slug>
Asset type: <where the asset will be used>
Primary request: <user's main prompt>
Input images: <Image 1: role; Image 2: role>
Scene/backdrop: <environment>
Subject: <main subject>
Style/medium: <photo/illustration/3D/etc>
Composition/framing: <wide/close/top-down; placement>
Lighting/mood: <lighting + mood>
Color palette: <palette notes>
Materials/textures: <surface details>
Text (verbatim): "<exact text>"
Constraints: <must keep/must avoid>
Avoid: <negative constraints>
```

## References

- `references/cli.md`: CLI usage.
- `references/image-api.md`: Gemini image API quick reference.
- `references/prompting.md`: prompt shaping and iteration.
- `references/sample-prompts.md`: copy/paste examples.
- `references/setup.md`: setup, API key, dependencies, and environment notes.
- `scripts/image_gen.py`: Gemini CLI implementation.
- `scripts/remove_chroma_key.py`: local transparent-background helper.
