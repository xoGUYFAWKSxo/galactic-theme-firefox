"""Build the theme's two animated layers.

Firefox draws ``theme_frame`` (the stars) over ``additional_backgrounds``
(the galaxy), and both over the solid ``frame`` color. Splitting the scene
this way lets each layer be a small palette APNG: the star layer is one tint
with 256 alpha levels, and the galaxy layer only changes inside its own box.
Together they stay well under AMO's 7 MB limit for themes.
"""
import math
import random
import struct
import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / 'images'

WIDTH = 2560
HEIGHT = 80             # Only the tab row shows the frame image; the toolbar is opaque.
SCENE_HEIGHT = 200      # Star targets keep the original 200 px layout.
FRAME_COLOR = (6, 9, 27)  # Matches manifest colors.frame (#06091b).
SCALE = 2

STAR_FPS = 15
STAR_SECONDS = 90        # Each star takes 90 s to fly from the center to the edge.
STAR_LOOP_SECONDS = 30   # Each lane holds 3 stars a third of a flight apart, so 30 s loops seamlessly.
STAR_CENTER = (2020, 24)
STAR_TINT = (205, 222, 255)
STAR_LANES = 600
GLOW_MIN_RADIUS = 1.3     # Only the largest stars get a halo; halos are the costliest pixels.
ALPHA_LEVELS = 32         # 32 alpha steps look the same and compress far better.

GALAXY_FPS = 15
GALAXY_SECONDS = 45
GALAXY_SIZE = 72
GALAXY_WIDTH = 400      # Aligned "right top", so the galaxy sits 200 px from the right edge.
GALAXY_CENTER = (GALAXY_WIDTH // 2, 24)


def chunk(stream, kind, payload):
    stream.write(struct.pack('>I', len(payload)) + kind + payload)
    stream.write(struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff))


def write_apng(path, width, height, palette, frames, count, fps):
    """Write palette frames (bytes of width*height indices) as a looping APNG."""
    num, den = (2, 25) if fps == 12.5 else (1, int(fps))
    with path.open('wb') as stream:
        stream.write(b'\x89PNG\r\n\x1a\n')
        chunk(stream, b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 3, 0, 0, 0))
        chunk(stream, b'PLTE', bytes(c for rgba in palette for c in rgba[:3]))
        chunk(stream, b'tRNS', bytes(rgba[3] for rgba in palette))
        chunk(stream, b'acTL', struct.pack('>II', count, 0))
        sequence = 0
        for index, pixels in enumerate(frames):
            rows = b''.join(b'\0' + pixels[y * width:(y + 1) * width] for y in range(height))
            data = zlib.compress(rows, 9)
            chunk(stream, b'fcTL', struct.pack('>IIIIIHHBB', sequence, width, height, 0, 0, num, den, 0, 0))
            sequence += 1
            if index == 0:
                chunk(stream, b'IDAT', data)
            else:
                chunk(stream, b'fdAT', struct.pack('>I', sequence) + data)
                sequence += 1
            if index % 150 == 0:
                print(f'  {path.name}: {index + 1}/{count}', flush=True)
        chunk(stream, b'IEND', b'')
    print(f'Created {path.name} ({path.stat().st_size:,} bytes)', flush=True)


def star_frames(count):
    rng = random.Random(73421)
    copies = STAR_SECONDS // STAR_LOOP_SECONDS
    stars = []
    for i in range(STAR_LANES):
        # Extra stars in the narrow visible tab row.
        target_y = rng.uniform(0, 50 if i % 2 == 0 else SCENE_HEIGHT)
        dx, dy = rng.uniform(0, WIDTH) - STAR_CENTER[0], target_y - STAR_CENTER[1]
        phase, radius, twinkles = rng.random(), rng.uniform(.4, 1.4), rng.random() < .32
        # Twinkle cycles per flight are multiples of 3, so twinkles also repeat every loop.
        offset, cycles = rng.uniform(0, math.tau), rng.choice([18, 30, 36])
        for copy in range(copies):
            stars.append((dx, dy, (phase + copy / copies) % 1, radius, twinkles, offset, cycles))
    for index in range(count):
        seconds = index / STAR_FPS
        layer = Image.new('RGBA', (WIDTH * SCALE, HEIGHT * SCALE))
        draw = ImageDraw.Draw(layer, 'RGBA')
        for dx, dy, phase, radius, twinkles, offset, cycles in stars:
            p = (phase + seconds / STAR_SECONDS) % 1
            zoom = .025 * 80 ** p
            x = (STAR_CENTER[0] + dx * zoom) * SCALE
            y = (STAR_CENTER[1] + dy * zoom) * SCALE
            if x < -8 or x > WIDTH * SCALE + 8 or y < -8 or y > HEIGHT * SCALE + 8:
                continue
            fade = min(1, p * 8) * min(1, (1 - p) * 10)
            pulse = .72 + .28 * math.sin(math.tau * cycles * seconds / STAR_SECONDS + offset) if twinkles else 1
            alpha = round(255 * fade * (.24 + .7 * p) * pulse)
            r = radius * (.32 + .9 * p) * SCALE
            white = (255, 255, 255)
            if radius >= GLOW_MIN_RADIUS:
                draw.ellipse((x - r * 3, y - r * 3, x + r * 3, y + r * 3), fill=(*white, round(alpha * .10)))
            if p > .68:
                draw.line((x, y, x - dx * zoom * .002 * SCALE, y - dy * zoom * .002 * SCALE),
                          fill=(*white, round(alpha * .24)), width=max(1, round(r * .6)))
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(*white, alpha))
        # One tint for every star, so the alpha channel is the whole image.
        alpha = layer.getchannel('A').reduce(SCALE)
        if ALPHA_LEVELS < 256:
            step = 255 / (ALPHA_LEVELS - 1)
            alpha = alpha.point(lambda a: round(round(a / step) * step))
        yield alpha


def galaxy_layer(galaxy, angle):
    """RGBA pixels of the galaxy layer at one rotation angle, flattened to (n, 4)."""
    rotated = galaxy.rotate(-angle, Image.Resampling.BICUBIC, expand=True)
    layer = Image.new('RGBA', (GALAXY_WIDTH * SCALE, HEIGHT * SCALE))
    layer.alpha_composite(rotated, (GALAXY_CENTER[0] * SCALE - rotated.width // 2,
                                    GALAXY_CENTER[1] * SCALE - rotated.height // 2))
    return np.asarray(layer.resize((GALAXY_WIDTH, HEIGHT), Image.Resampling.LANCZOS)).reshape(-1, 4)


def galaxy_palette(galaxy):
    """Shared 256-entry palette: index 0 is transparent, 1-255 from sample angles."""
    samples = np.concatenate([galaxy_layer(galaxy, angle) for angle in range(0, 360, 10)])
    opaque = samples[samples[:, 3] >= 8]
    strip = Image.fromarray(np.ascontiguousarray(opaque.reshape(1, -1, 4)), 'RGBA')
    quantized = strip.quantize(255, method=Image.Quantize.FASTOCTREE)
    colors = quantized.getpalette('RGBA')[:255 * 4]
    entries = [tuple(colors[i:i + 4]) for i in range(0, len(colors), 4)]
    return [(0, 0, 0, 0)] + entries + [(0, 0, 0, 0)] * (255 - len(entries))


def galaxy_frames(galaxy, palette, count):
    table = np.array(palette[1:], dtype=np.float32)
    weights = np.array([1, 1, 1, 1.5], dtype=np.float32)
    for index in range(count):
        pixels = galaxy_layer(galaxy, 360 * index / count)
        indices = np.zeros(len(pixels), dtype=np.uint8)
        visible = pixels[:, 3] >= 8
        colors = pixels[visible].astype(np.float32)
        distance = (((colors[:, None, :] - table[None, :, :]) * weights) ** 2).sum(axis=2)
        indices[visible] = distance.argmin(axis=1) + 1
        yield indices.tobytes()


def save_preview(stars_first, galaxy_first, palette):
    scene = Image.new('RGBA', (WIDTH, HEIGHT), (*FRAME_COLOR, 255))
    galaxy = Image.new('P', (GALAXY_WIDTH, HEIGHT))
    galaxy.putpalette([c for rgba in palette for c in rgba], 'RGBA')
    galaxy.frombytes(galaxy_first)
    scene.alpha_composite(galaxy.convert('RGBA'), (WIDTH - GALAXY_WIDTH, 0))
    stars = Image.new('RGBA', (WIDTH, HEIGHT), STAR_TINT)
    stars.putalpha(stars_first)
    scene.alpha_composite(stars)
    scene.convert('RGB').save(ROOT / 'preview.png', optimize=True)


def main():
    IMAGES.mkdir(exist_ok=True)
    only = set(sys.argv[1:]) or {'stars', 'galaxy'}
    star_count = round(STAR_FPS * STAR_LOOP_SECONDS)
    galaxy_count = GALAXY_FPS * GALAXY_SECONDS
    galaxy = Image.open(ROOT / 'artwork' / 'galactic-tab-galaxy.png').convert('RGBA')
    galaxy = galaxy.resize((GALAXY_SIZE * SCALE, GALAXY_SIZE * SCALE), Image.Resampling.LANCZOS)
    palette = galaxy_palette(galaxy)
    if 'galaxy' in only:
        write_apng(IMAGES / 'galaxy.png', GALAXY_WIDTH, HEIGHT, palette,
                   galaxy_frames(galaxy, palette, galaxy_count), galaxy_count, GALAXY_FPS)
    if 'stars' in only:
        tint = [(*STAR_TINT, alpha) for alpha in range(256)]
        write_apng(IMAGES / 'stars.png', WIDTH, HEIGHT, tint,
                   (frame.tobytes() for frame in star_frames(star_count)), star_count, STAR_FPS)
    save_preview(next(star_frames(1)), next(galaxy_frames(galaxy, palette, galaxy_count)), palette)


if __name__ == '__main__':
    main()
