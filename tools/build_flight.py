"""Build the forward-flight toolbar animation with bounded memory."""
import io
import math
import random
import struct
import zlib
from PIL import Image, ImageDraw
from build_theme_art import ROOT, WIDTH, HEIGHT

FPS = 25
SECONDS = 90
FRAMES = FPS * SECONDS
CENTER = (2020, 24)
# Keep the galaxy just left of the tab-list arrow and window controls.
GALAXY_CENTER = (WIDTH - 200, 24)
SCALE = 2


def chunk(stream, kind, payload):
    stream.write(struct.pack('>I', len(payload)) + kind + payload)
    stream.write(struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff))


def main():
    rng = random.Random(73421)
    stars = []
    for i in range(1800):
        # Extra stars in the narrow visible tab row.
        target_y = rng.uniform(0, 50 if i % 2 == 0 else HEIGHT)
        stars.append((rng.uniform(0, WIDTH) - CENTER[0], target_y - CENTER[1],
                      rng.random(), rng.uniform(.4, 1.4), rng.random() < .32,
                      rng.uniform(0, math.tau), rng.choice([18, 30, 36])))
    base = Image.new('RGB', (WIDTH * SCALE, HEIGHT * SCALE))
    draw = ImageDraw.Draw(base)
    for y in range(HEIGHT * SCALE):
        f = y / (HEIGHT * SCALE)
        draw.line((0, y, WIDTH * SCALE, y), fill=(round(4+3*f), round(6+4*f), round(18+12*f)))
    galaxy = Image.open(ROOT / "artwork" / "galactic-tab-galaxy.png").convert("RGBA").resize((72 * SCALE, 72 * SCALE), Image.Resampling.LANCZOS)
    output = ROOT / 'images' / 'galaxy-header.png'
    with output.open('wb') as stream:
        stream.write(b'\x89PNG\r\n\x1a\n')
        sequence = 0
        palette = None
        for index in range(FRAMES):
            seconds = index / FPS
            frame = base.copy()
            draw = ImageDraw.Draw(frame, 'RGBA')
            for dx, dy, phase, radius, twinkles, offset, cycles in stars:
                p = (phase + seconds / 90) % 1
                zoom = .025 * 80 ** p
                x = (CENTER[0] + dx * zoom) * SCALE
                y = (CENTER[1] + dy * zoom) * SCALE
                if x < -8 or x > WIDTH * SCALE + 8 or y < -8 or y > HEIGHT * SCALE + 8:
                    continue
                fade = min(1, p*8) * min(1, (1-p)*10)
                pulse = .72 + .28 * math.sin(math.tau * cycles * seconds / SECONDS + offset) if twinkles else 1
                alpha = round(255 * fade * (.24 + .7*p) * pulse)
                r = radius * (.32 + .9*p) * SCALE
                draw.ellipse((x-r*3, y-r*3, x+r*3, y+r*3), fill=(180, 205, 255, round(alpha*.10)))
                if p > .68:
                    draw.line((x, y, x-dx*zoom*.002*SCALE, y-dy*zoom*.002*SCALE), fill=(199,220,255,round(alpha*.24)), width=max(1,round(r*.6)))
                draw.ellipse((x-r, y-r, x+r, y+r), fill=(209,225,255,alpha))
            rotated = galaxy.rotate(-360*seconds/45, Image.Resampling.BICUBIC, expand=True)
            frame.paste(rotated, (round(GALAXY_CENTER[0]*SCALE-rotated.width/2), round(GALAXY_CENTER[1]*SCALE-rotated.height/2)), rotated)
            frame = frame.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
            if index == 0:
                frame.save(ROOT / 'preview.png')
                palette = frame.quantize(colors=256)
                chunk(stream, b'IHDR', struct.pack('>IIBBBBB', WIDTH, HEIGHT, 8, 3, 0, 0, 0))
                chunk(stream, b'PLTE', bytes(palette.getpalette()))
                chunk(stream, b'acTL', struct.pack('>II', FRAMES, 0))
            frame = frame.quantize(palette=palette, dither=Image.Dither.NONE)
            encoded = io.BytesIO()
            frame.save(encoded, format='PNG', compress_level=6)
            data = encoded.getvalue()
            position = 8
            compressed = []
            while position < len(data):
                length = struct.unpack('>I', data[position:position+4])[0]
                if data[position+4:position+8] == b'IDAT':
                    compressed.append(data[position+8:position+8+length])
                position += 12 + length
            chunk(stream, b'fcTL', struct.pack('>IIIIIHHBB', sequence, WIDTH, HEIGHT, 0, 0, 1, FPS, 0, 0))
            sequence += 1
            payload = b''.join(compressed)
            if index == 0:
                chunk(stream, b'IDAT', payload)
            else:
                chunk(stream, b'fdAT', struct.pack('>I', sequence) + payload)
                sequence += 1
            if index % 225 == 0:
                print(f'Rendered {index + 1}/{FRAMES} frames', flush=True)
        chunk(stream, b'IEND', b'')
    print(f'Created {output} ({output.stat().st_size:,} bytes)', flush=True)


if __name__ == '__main__':
    main()
