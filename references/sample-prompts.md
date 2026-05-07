# Gemini image prompt examples

These examples are prompt recipes for `scripts/image_gen.py`.

## Product hero

```text
Use case: product-mockup
Asset type: landing page hero
Primary request: a minimal hero image of a matte ceramic coffee mug
Scene/backdrop: clean stone surface with soft neutral background
Style/medium: photorealistic studio product photography
Composition/framing: wide 16:9 composition with usable negative space
Lighting/mood: soft daylight, gentle shadows
Constraints: no logos, no text, no watermark
```

Command:

```bash
python scripts/image_gen.py generate \
  --prompt "a minimal hero image of a matte ceramic coffee mug" \
  --use-case product-mockup \
  --asset-type "landing page hero" \
  --style "photorealistic studio product photography" \
  --composition "wide composition with usable negative space" \
  --aspect-ratio 16:9 \
  --image-size 2K \
  --out output/imagegen/mug-hero.png
```

## Editorial infographic

```text
Use case: infographic-diagram
Asset type: article illustration
Primary request: explain how solar panels convert sunlight into household electricity
Style/medium: clean editorial infographic
Composition/framing: three-step left-to-right process with clear arrows
Text (verbatim): "SUNLIGHT", "SOLAR PANEL", "INVERTER", "HOME POWER"
Constraints: readable labels, no extra words, scientifically reasonable flow
```

Use `gemini-3-pro-image-preview` when label fidelity matters:

```bash
python scripts/image_gen.py generate \
  --model gemini-3-pro-image-preview \
  --prompt "explain how solar panels convert sunlight into household electricity" \
  --use-case infographic-diagram \
  --text "SUNLIGHT, SOLAR PANEL, INVERTER, HOME POWER" \
  --aspect-ratio 16:9 \
  --image-size 2K \
  --out output/imagegen/solar-infographic.png
```

## Background replacement edit

```text
Use case: precise-object-edit
Asset type: product photo background replacement
Input images: Image 1 is the edit target
Primary request: replace only the background with a warm sunset gradient
Constraints: keep the product, label text, edges, camera angle, and lighting unchanged; no extra text; no watermark
```

Command:

```bash
python scripts/image_gen.py edit \
  --image input/product.png \
  --prompt "replace only the background with a warm sunset gradient; keep the product, label text, edges, camera angle, and lighting unchanged" \
  --aspect-ratio 1:1 \
  --out output/imagegen/product-sunset.png
```

## Reference-image guided generation

```text
Use case: stylized-concept
Asset type: website hero image
Input images: Image 1 is a style reference only
Primary request: create a new hero image for an AI image generation tool
Style/medium: use the reference for color, lighting, and material feel
Composition/framing: wide 16:9 composition with clean negative space
Constraints: do not copy text, logos, exact layout, or identifiable proprietary elements from the reference
Avoid: watermark, readable text, brand marks
```

Command:

```bash
python scripts/image_gen.py generate \
  --reference-image input/style-reference.png \
  --prompt "create a new hero image for an AI image generation tool; use Image 1 only for color, lighting, and material feel; do not copy text, logos, exact layout, or identifiable proprietary elements" \
  --aspect-ratio 16:9 \
  --out output/imagegen/reference-hero.png
```

## Multi-image compositing

```text
Use case: compositing
Asset type: campaign visual
Input images: Image 1 is the base room; Image 2 is the product to place on the table
Primary request: place the product from Image 2 naturally onto the table in Image 1
Constraints: match perspective, scale, shadows, and lighting; keep the room layout unchanged; no extra objects; no text
```

Command:

```bash
python scripts/image_gen.py edit \
  --image input/room.png \
  --image input/product.png \
  --prompt "place the product from Image 2 naturally onto the table in Image 1; match perspective, scale, shadows, and lighting; keep the room layout unchanged" \
  --out output/imagegen/composite.png
```

## Batch JSONL

```jsonl
{"prompt":"A tactile 3D app icon for a habit tracker, no text","use_case":"logo-brand","aspect_ratio":"1:1","out":"habit-icon.png"}
{"prompt":"A cozy reading nook at dusk, editorial photography","use_case":"photorealistic-natural","aspect_ratio":"4:3","out":"reading-nook.png"}
{"prompt":"A clean dashboard mockup for monthly sales analysis","use_case":"ui-mockup","aspect_ratio":"16:9","out":"sales-dashboard.png"}
```
