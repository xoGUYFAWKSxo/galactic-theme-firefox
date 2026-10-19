from pathlib import Path
import random

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "artwork" / "galaxy-source.png"
DESTINATION = ROOT / "images" / "galaxy-header.png"
PREVIEW = ROOT / "preview.png"

WIDTH = 2560
HEIGHT = 200
FRAME_COUNT = 675
FRAME_DURATION_MS = 67  # About 45 seconds per full revolution at 15 fps.
STAR_DRIFT_X_PX_PER_SECOND = 2.0
STAR_DRIFT_Y_PX_PER_SECOND = 0.45


def make_star_field() -> Image.Image:
    field = Image.new("RGB", (WIDTH, HEIGHT))
    pixels = field.load()
    for y in range(HEIGHT):
        blend = y / max(1, HEIGHT - 1)
        color = (
            round(4 + blend * 3),
            round(6 + blend * 4),
            round(18 + blend * 12),
        )
        for x in range(WIDTH):
            pixels[x, y] = color

    glow = Image.new("RGBA", field.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    points = []
    rng = random.Random(73421)
    for _ in range(430):
        x = rng.randrange(WIDTH)
        y = rng.randrange(HEIGHT)
        radius = rng.choices([0, 1, 2], weights=[0.64, 0.31, 0.05])[0]
        brightness = rng.randrange(80, 205)
        color = rng.choice([
            (162, 190, 255),
            (203, 215, 255),
            (164, 179, 241),
            (240, 221, 255),
        ])
        points.append((x, y, radius, color, brightness))
        if radius == 2:
            glow_draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(*color, 24))
        glow_draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*color, brightness))

    glow = glow.filter(ImageFilter.GaussianBlur(2))
    field = Image.alpha_composite(field.convert("RGBA"), glow)
    crisp_stars = Image.new("RGBA", field.size, (0, 0, 0, 0))
    crisp_draw = ImageDraw.Draw(crisp_stars)
    for x, y, radius, color, brightness in points:
        crisp_draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*color, brightness))
        if radius == 2:
            crisp_draw.point((x, y), fill=(255, 255, 255, 240))
    return Image.alpha_composite(field, crisp_stars)


def make_galaxy_cutout() -> Image.Image:
    source = Image.open(SOURCE).convert("RGB")
    source_pixels = source.load()
    alpha = Image.new("L", source.size)
    alpha_pixels = alpha.load()

    # The source is a glowing spiral over a near-black sky. This luminance
    # matte keeps the luminous galaxy and soft arms while dropping that sky.
    for y in range(source.height):
        for x in range(source.width):
            r, g, b = source_pixels[x, y]
            luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
            alpha_pixels[x, y] = max(0, min(255, round((luminance - 8) * 2.6)))

    source.putalpha(alpha.filter(ImageFilter.GaussianBlur(1.0)))
    return source


def make_galaxy_layer() -> Image.Image:
    source = make_galaxy_cutout().resize((72, 72), Image.Resampling.LANCZOS)
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    layer.alpha_composite(source, (1984, -12))
    return layer


def tile_star_field(stars: Image.Image) -> Image.Image:
    tiled = Image.new("RGBA", (WIDTH * 2, HEIGHT * 2))
    for x in (0, WIDTH):
        for y in (0, HEIGHT):
            tiled.paste(stars, (x, y))
    return tiled


def make_frame(tiled_stars: Image.Image, galaxy: Image.Image, frame_number: int) -> Image.Image:
    # Fractional resampling makes the low-speed star drift move smoothly
    # instead of holding still and jumping one pixel at a time.
    seconds = frame_number * FRAME_DURATION_MS / 1000
    star_x = seconds * STAR_DRIFT_X_PX_PER_SECOND
    star_y = seconds * STAR_DRIFT_Y_PX_PER_SECOND
    frame = tiled_stars.transform(
        (WIDTH, HEIGHT),
        Image.Transform.AFFINE,
        (1, 0, star_x, 0, 1, star_y),
        resample=Image.Resampling.BICUBIC,
    )

    angle = -(360 * frame_number / FRAME_COUNT)
    rotated = galaxy.rotate(angle, resample=Image.Resampling.BICUBIC, center=(2020, 24))
    frame.alpha_composite(rotated)
    return frame.convert("RGB")


def main() -> None:
    stars = tile_star_field(make_star_field())
    galaxy = make_galaxy_layer()
    cutout_path = ROOT / "images" / "galaxy-cutout.png"
    make_galaxy_cutout().save(cutout_path, optimize=True)
    frames = [make_frame(stars, galaxy, index) for index in range(FRAME_COUNT)]
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        DESTINATION,
        format="PNG",
        save_all=True,
        append_images=frames[1:],
        duration=FRAME_DURATION_MS,
        loop=0,
        optimize=True,
        compress_level=9,
    )
    frames[0].save(PREVIEW, format="PNG", optimize=True)
    print(f"Created {DESTINATION} ({DESTINATION.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
