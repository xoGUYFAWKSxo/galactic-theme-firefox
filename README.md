# Galactic Theme

Animated Firefox theme with a detailed spiral galaxy and a gently moving, twinkling starfield.

## Features
- Galaxy near the tab-list arrow, 200 pixels from the right edge.
- Stars take 90 seconds to fly past; galaxy rotates every 45 seconds.
- Two 15 fps animated PNG layers (stars and galaxy) with matching Galactic Tab artwork, about 6 MB in total.
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

Generated animation assets are included, so loading does not require a build. `tools/build_flight.py` writes `images/stars.png` (the transparent `theme_frame`), `images/galaxy.png` (an `additional_backgrounds` layer) and `preview.png`. Pass `stars` or `galaxy` to rebuild one layer.

addons.mozilla.org rejects themes over 7 MB. The star layer loops every 30 seconds (each star has two twins a third of a flight apart) so the theme stays near 6 MB; check the size of `galactic-theme.xpi` after changing frame rates, star counts or dimensions.

## Related extension
[Galactic Tab](https://github.com/xoGUYFAWKSxo/galactic-tab-firefox) provides the custom new-tab page and optional browser-strip controls. Enabling those controls overrides this theme until they are switched off.

## Artwork and privacy
The detailed galaxy artwork was generated from the project's original galaxy reference. This theme makes no network requests and collects no browsing data.
