# Hyakki Yagyō with video layers

A IIIF Presentation 3.0 manifest of the handscroll *Hyakki Yagyō-zu* (百鬼夜行図, The University of Tokyo General Library), with 19 short AI-generated clips that make some of its figures move.

The manifest has the same shape as IIIF Cookbook recipe [0036 Composition from Multiple Images](https://iiif.io/api/cookbook/recipe/0036-composition-from-multiple-images/): a base image, plus more resources painted onto regions of the Canvas with `#xywh=`. Here each added resource is a `Video` instead of an `Image`. The Canvas has no `duration`. The text that describes each motion (the prompt used to generate the clip) is kept as the video's `summary`.

- Manifest: https://nakamura196.github.io/hyakki-video-layers/manifest.json
- View in IIIF Kasane: https://kasane.ldas.jp/en/viewer?manifest=https%3A%2F%2Fnakamura196.github.io%2Fhyakki-video-layers%2Fmanifest.json&tab=layers

## Contents

- `manifest.json`: the manifest
- `videos/`: the clips (MP4, 19 files, about 124 MB)
- `scripts/convert.py`: makes `manifest.json` from the manifest of the original IIIF Animated Viewer (where the videos were in `canvas.annotations` with a describing text body)

The clips were generated from crops of the IIIF image with a video generation model, then placed back on the regions they came from.

## Rights

The base image is served by the IIIF Image API of The University of Tokyo. See the manifest's `requiredStatement` for attribution. The clips are modified versions of that image.
