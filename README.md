# Gemini ImageGen

**繁體中文** | [English](README.en.md)

Gemini ImageGen 是一個使用 Gemini / Nano Banana 圖像模型的產圖 skill 與 Python CLI。它可以產生新的點陣圖、用文字加圖片進行編輯，並批次生成多組提示詞。

這個專案可以用兩種方式使用：

- 作為通用 CLI：透過 `scripts/image_gen.py` 執行。
- 作為 skill package：透過 `SKILL.md` 與 `agents/gemini.yaml` 整合。

## 功能

- 使用 Gemini 圖像模型進行文字產圖。
- 使用參考圖引導新圖片的風格、構圖或視覺方向。
- 使用一張或多張輸入圖片進行文字加圖片編輯。
- 支援 JSONL 批次生成。
- 提供常見素材工作流的 prompt augmentation 欄位。
- 本機輸出管理，預設避免覆蓋既有檔案。
- 可選擇輸出較小的 web 版圖片。

## 需求

- Python 3.10 或更新版本。
- Gemini API key。
- `google-genai`。
- `pillow`，用於輸出較小的 web 版圖片。

安裝依賴：

```bash
python -m pip install google-genai pillow
```

## API Key

設定其中一個環境變數：

```bash
export GEMINI_API_KEY="your-key"
```

PowerShell：

```powershell
$env:GEMINI_API_KEY = "your-key"
```

CLI 也支援本機開發用的 `.env.txt`。內容可以是：

```text
GEMINI_API_KEY=your-key
```

或只有一行 raw API key。

請不要提交 `.env.txt`。

## 快速開始

先用 dry-run 檢查 request，不會使用網路或額度：

```bash
python scripts/image_gen.py generate \
  --prompt "A clean product-style image of a ceramic mug" \
  --aspect-ratio 1:1 \
  --out output/imagegen/mug.png \
  --dry-run
```

產生圖片：

```bash
python scripts/image_gen.py generate \
  --prompt "A clean 3D illustration of a modern laptop on a desk, colorful abstract canvas on screen, no text, no logos" \
  --out output/imagegen/workspace.png
```

使用參考圖生成新圖片：

```bash
python scripts/image_gen.py generate \
  --reference-image input/style-reference.png \
  --prompt "Create a new landing page hero image using the reference image only for visual style; do not copy any text or logo" \
  --out output/imagegen/hero-from-reference.png
```

編輯圖片：

```bash
python scripts/image_gen.py edit \
  --image input/product.png \
  --prompt "Replace only the background with a warm sunset gradient; keep the product, label text, edges, and camera angle unchanged" \
  --out output/imagegen/product-sunset.png
```

## 模型

預設模型：

```text
gemini-3.1-flash-image-preview
```

其他常用選項：

```text
gemini-3-pro-image-preview
gemini-2.5-flash-image
```

使用 `--model` 指定模型：

```bash
python scripts/image_gen.py generate \
  --model gemini-3-pro-image-preview \
  --prompt "A premium editorial product image of a ceramic mug" \
  --out output/imagegen/mug-premium.png
```

## 批次生成

建立 `tmp/imagegen/prompts.jsonl`：

```jsonl
{"prompt":"A tactile 3D app icon for a habit tracker, no text","use_case":"logo-brand","aspect_ratio":"1:1","out":"habit-icon.png"}
{"prompt":"A cozy reading nook at dusk, editorial photography","use_case":"photorealistic-natural","aspect_ratio":"4:3","out":"reading-nook.png"}
```

執行：

```bash
python scripts/image_gen.py generate-batch \
  --input tmp/imagegen/prompts.jsonl \
  --out-dir output/imagegen/batch \
  --concurrency 5
```

## 透明背景

目前不支援透明背景輸出。Gemini ImageGen 只負責產生或編輯一般點陣圖；如果需要高品質透明背景，建議使用專門的去背工具或手動修圖流程。

## 專案結構

- `SKILL.md`：skill 使用規則。
- `agents/gemini.yaml`：skill metadata。
- `scripts/image_gen.py`：Gemini image CLI。
- `references/`：使用、環境與 prompt 補充文件。
- `tests/`：CLI 行為測試。

## 驗證

執行：

```bash
python -B -m unittest tests.test_image_gen -v
```

## 授權

請見 `LICENSE.txt`。
