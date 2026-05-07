# Gemini image prompting best practices

These principles apply to Gemini / Nano Banana image generation and editing through `scripts/image_gen.py`.

## Structure

Use a consistent order:

```text
Use case:
Asset type:
Primary request:
Input images:
Scene/backdrop:
Subject:
Style/medium:
Composition/framing:
Lighting/mood:
Color palette:
Materials/textures:
Text (verbatim):
Constraints:
Avoid:
```

Keep the prompt concise. Add only details that materially improve the image.

## Specificity

- If the user prompt is already detailed, normalize it without inventing new requirements.
- If the prompt is generic, add useful framing, medium, polish level, and intended use.
- Do not add unrelated characters, props, brand names, slogans, palettes, or story beats.

## Composition

- Specify framing when it matters: close-up, wide, top-down, isometric, full body, product-centered.
- Mention negative space when the image will sit behind UI or page copy.
- Avoid arbitrary left/right placement unless the consuming layout requires it.

## Text in images

- Put literal text in quotes.
- Ask for verbatim rendering and no extra characters.
- Use `gemini-3-pro-image-preview` for dense text, magazine/editorial mockups, infographics, labels, or diagrams where text fidelity matters.

## Input images

Label each input image:

```text
Input images: Image 1 is the edit target; Image 2 is a style reference.
```

For reference-image generation, say that the image is not an edit target:

```text
Input images: Image 1 is a style reference only.
Primary request: create a new image inspired by the color, lighting, and material feel.
Constraints: do not copy text, logos, exact layout, or identifiable proprietary elements.
```

If preserving an existing image, repeat invariants:

```text
Change only the background. Keep the product, label text, edges, camera angle, and lighting unchanged.
```

## Iteration

- Start with a clean base prompt.
- Make one targeted change per retry.
- Restate invariants every time.

## Transparent images

For simple opaque subjects, use chroma-key prompting:

```text
Create the requested subject on a perfectly flat solid #00ff00 chroma-key background for local background removal.
The background must be one uniform color with no shadows, gradients, texture, floor plane, or lighting variation.
Keep crisp edges and generous padding.
Do not use #00ff00 anywhere in the subject.
```

Then run:

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

Complex subjects such as hair, glass, smoke, liquids, translucent materials, reflections, and soft shadows may need manual cleanup or iteration.

## Use-case tips

- `photorealistic-natural`: Use photography language and concrete real-world textures.
- `product-mockup`: Describe materials, surface, label clarity, and clean silhouette.
- `ui-mockup`: Ask for practical UI hierarchy and readable controls, not concept art.
- `infographic-diagram`: Define audience, layout flow, required labels, and readable typography.
- `logo-brand`: Keep it simple, balanced, and vector-friendly even though output is bitmap.
- `ads-marketing`: Include audience, product position, scene, and exact tagline if needed.
- `scientific-educational`: State required labels, accuracy constraints, and clean whitespace.
- `style-transfer`: Name style cues to preserve and what must change.
- `compositing`: Explain which image contributes which subject and how they should interact.
