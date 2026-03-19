from PIL import Image


def average_hash(image: Image.Image, hash_size: int = 8) -> int:
    img = image.convert("L").resize((hash_size, hash_size))
    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    bits = 0
    for idx, pixel in enumerate(pixels):
        if pixel >= avg:
            bits |= 1 << idx
    return bits


def hamming_distance(a: int, b: int) -> int:
    return (a ^ b).bit_count()
