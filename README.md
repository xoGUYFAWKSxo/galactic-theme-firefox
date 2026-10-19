# Galactic Theme

Animated Firefox theme with a detailed spiral galaxy and a gently moving, twinkling starfield.

## Features
- Galaxy near the tab-list arrow, 200 pixels from the right edge.
- Stars travel on a 90-second cycle; galaxy rotates every 45 seconds.
- 25 fps animated PNG with matching Galactic Tab artwork.
- Dark toolbar and readable tab colors.

## Load for development
1. Download or clone this repository.
2. In Firefox, open `about:debugging#/runtime/this-firefox`.
3. Choose **Load Temporary Add-on** and select `manifest.json`.

Temporary add-ons disappear on restart. Persistent installation requires Mozilla signing. The generated XPI is unsigned.

## Build
Python 3.10+ is required for the build scripts.

```sh
python -m pip install -r requirements.txt
python tools/build_flight.py
python tools/package.py
```

Generated animation assets are included, so loading does not require a build. Animation rebuilding can take a few minutes. `tools/build_flight.py` is the current generator; `build_theme_art.py` supplies shared dimensions and retains the original artwork workflow.

## Related extension
[Galactic Tab](https://github.com/xoGUYFAWKSxo/galactic-tab-firefox) provides the custom new-tab page and optional browser-strip controls. Enabling those controls overrides this theme until they are switched off.

## Artwork and privacy
The detailed galaxy artwork was generated from the project's original galaxy reference. This theme makes no network requests and collects no browsing data.
