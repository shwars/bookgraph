"""Generate Alice AI ART images and key out a solid screen locally."""

import argparse
import base64
import binascii
from collections.abc import Iterator
from http.client import HTTPException
import io
from pathlib import Path
import re
from statistics import median
import sys
from urllib.error import HTTPError
from urllib.request import urlopen

from PIL import Image, ImageChops, ImageMath, UnidentifiedImageError


CREDENTIALS_URL = "https://storage.yandexcloud.net/shwars/temp/imagen.env"
API_URL = "https://ai.api.cloud.yandex.net/v1"
MODEL_NAME = "aliceai-image-art-3.0"
PROMPT_LIMIT = 500
SIZES = ("1024x1024", "1024x1536", "1536x1024")
KEY_COLORS = {"green": "ярко-зелёный (#00FF00)", "magenta": "пурпурный (#FF00FF)"}
OUTPUT_FORMATS = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG"}


class ImagenError(Exception):
    """An error safe to display in the CLI."""


def read_credentials() -> tuple[str, str]:
    from dotenv import dotenv_values

    limit = 16_384
    try:
        with urlopen(CREDENTIALS_URL, timeout=20) as response:
            payload = response.read(limit + 1)
    except HTTPError as error:
        raise ImagenError(f"Загрузка imagen.env завершилась с HTTP {error.code}.") from None
    except (OSError, HTTPException):
        raise ImagenError("Не удалось загрузить imagen.env по HTTPS.") from None
    if len(payload) > limit:
        raise ImagenError("Ответ при загрузке imagen.env превышает допустимый размер.")
    try:
        content = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ImagenError("Ожидается imagen.env в кодировке UTF-8.") from None

    values = dotenv_values(stream=io.StringIO(content), interpolate=False)
    folder_id = (values.get("folder_id") or "").strip()
    api_key = (values.get("api_key") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", folder_id) or not re.fullmatch(r"[!-~]+", api_key):
        raise ImagenError("В imagen.env нужны корректные значения folder_id и api_key.")
    return folder_id, api_key


def make_prompt(text: str, key_color: str | None = None) -> str:
    prompt = text.strip()
    if not prompt:
        raise ImagenError("Промпт пуст.")
    if key_color is not None:
        prompt += (
            f"\nРовный сплошной фон {KEY_COLORS[key_color]}, без фактуры и градиента. "
            "Без пола и падающих теней. Свободные поля вокруг силуэта. Цвет фона только на фоне."
        )
    if len(prompt) > PROMPT_LIMIT:
        raise ImagenError(f"Промпт занимает {len(prompt)} символов. Лимит — {PROMPT_LIMIT}.")
    return prompt


def request_image(prompt: str, size: str) -> tuple[Image.Image, bytes]:
    from openai import APIConnectionError, APIError, APIStatusError, OpenAI

    folder_id, api_key = read_credentials()
    try:
        with OpenAI(
            base_url=API_URL,
            api_key=api_key,
            project=folder_id,
            timeout=180,
            max_retries=0,
        ) as client:
            response = client.images.generate(
                model=f"art://{folder_id}/{MODEL_NAME}", prompt=prompt, size=size
            )
    except APIStatusError as error:
        raise ImagenError(f"Запрос к Alice AI ART завершился с HTTP {error.status_code}.") from None
    except APIConnectionError:
        raise ImagenError("Не удалось получить ответ Alice AI ART. Проверьте доступ к API.") from None
    except (APIError, ValueError):
        raise ImagenError("Ошибка запроса или ответа Alice AI ART.") from None

    items = getattr(response, "data", None)
    encoded = getattr(items[0], "b64_json", None) if items else None
    if not encoded:
        raise ImagenError("Alice AI ART не вернула изображение в поле b64_json.")
    try:
        content = base64.b64decode(encoded, validate=True)
        image = Image.open(io.BytesIO(content))
        image.load()
    except (binascii.Error, OSError, ValueError, TypeError, Image.DecompressionBombError):
        raise ImagenError("Не удалось декодировать изображение из ответа Alice AI ART.") from None
    return image, content


def perimeter(size: tuple[int, int]) -> Iterator[tuple[int, int]]:
    width, height = size
    for x in range(width):
        yield x, 0
        yield x, height - 1
    for y in range(1, height - 1):
        yield 0, y
        yield width - 1, y


def alpha_ramp(strength: Image.Image, opaque_at: int, transparent_at: int) -> Image.Image:
    return strength.point([
        round(255 * min(1, max(0, (transparent_at - value) / (transparent_at - opaque_at))))
        for value in range(256)
    ])


def remove_screen(image: Image.Image, key_color: str) -> Image.Image:
    if min(image.size) < 3:
        raise ImagenError("Изображение слишком мало для оценки фона по краям.")
    if image.convert("RGBA").getchannel("A").getextrema() != (255, 255):
        raise ImagenError("Для cutout нужен непрозрачный исходник с хромакеем.")

    rgb = image.convert("RGB")
    red, green, blue = rgb.split()
    if key_color == "green":
        peak = green
        strength = ImageChops.subtract(green, ImageChops.lighter(red, blue))
    else:
        peak = ImageChops.lighter(red, blue)
        strength = ImageChops.subtract(ImageChops.darker(red, blue), green)

    edge = list(perimeter(rgb.size))
    screen_points = [point for point in edge if strength.getpixel(point) >= 48]
    if len(screen_points) < 0.85 * len(edge):
        raise ImagenError(f"Края кадра не покрыты хромакеем {key_color}.")

    screen_strengths = sorted(strength.getpixel(point) for point in screen_points)
    # The lower decile tolerates slight variation in the generated backdrop.
    transparent_at = screen_strengths[len(screen_strengths) // 10] - 6
    absolute_alpha = alpha_ramp(strength, opaque_at=12, transparent_at=transparent_at)

    # A shaded screen can retain its hue while its absolute chroma drops.
    relative_strength = ImageMath.lambda_eval(
        lambda args: args["convert"](args["strength"] * 255 / args["peak"], "L"),
        strength=strength,
        peak=ImageChops.lighter(peak, Image.new("L", peak.size, 1)),
    )
    screen_ratios = sorted(relative_strength.getpixel(point) for point in screen_points)
    relative_clear = screen_ratios[len(screen_ratios) // 10] * 3 // 4
    relative_alpha = alpha_ramp(relative_strength, relative_clear - 24, relative_clear)
    # Near black, a small channel difference gives an unreliable ratio.
    low_chroma = strength.point([255] * 32 + [0] * 224)
    alpha = ImageChops.darker(absolute_alpha, ImageChops.lighter(relative_alpha, low_chroma))
    if alpha.getextrema() != (0, 255):
        raise ImagenError("Хромакей не отделил прозрачный фон от непрозрачного объекта.")

    screen_pixels = [rgb.getpixel(point) for point in screen_points]
    screen_rgb = [round(median(channel)) for channel in zip(*screen_pixels)]
    safe_alpha = ImageChops.lighter(absolute_alpha, Image.new("L", alpha.size, 1))
    clear_pixels = alpha.point([255] + [0] * 255)

    def unmix(channel: Image.Image, screen: int) -> Image.Image:
        # Invert C = alpha * foreground + (1 - alpha) * screen on the soft edge.
        unmixed = ImageMath.lambda_eval(
            lambda args: args["convert"](
                (args["channel"] - screen) * 255 / args["alpha"] + screen, "L"
            ),
            channel=channel,
            alpha=safe_alpha,
        )
        unmixed.paste(0, mask=clear_pixels)
        return unmixed

    return Image.merge("RGBA", (
        unmix(red, screen_rgb[0]),
        unmix(green, screen_rgb[1]),
        unmix(blue, screen_rgb[2]),
        alpha,
    ))


def output_format(path: Path, *, transparent: bool) -> str:
    fmt = OUTPUT_FORMATS.get(path.suffix.lower())
    if transparent and fmt != "PNG":
        raise ImagenError("Для прозрачного изображения укажите выходной файл .png.")
    if fmt is None:
        raise ImagenError("Выходной файл должен иметь расширение .png, .jpg или .jpeg.")
    return fmt


def require_new(path: Path) -> None:
    if path.exists() or path.is_symlink():
        raise ImagenError(f"Выходной путь уже существует: {path}")


def write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        stream = path.open("xb")
    except FileExistsError:
        raise ImagenError(f"Выходной путь уже существует: {path}") from None
    try:
        with stream:
            stream.write(data)
    except OSError:
        path.unlink(missing_ok=True)
        raise


def encode_image(image: Image.Image, fmt: str) -> bytes:
    buffer = io.BytesIO()
    if fmt == "JPEG":
        image.convert("RGB").save(buffer, fmt, quality=95)
    else:
        image.save(buffer, fmt)
    return buffer.getvalue()


def generate(args: argparse.Namespace) -> None:
    fmt = output_format(args.output, transparent=args.transparent)
    require_new(args.output)
    key_color = (args.key_color or "green") if args.transparent else None
    if args.key_color and not args.transparent:
        raise ImagenError("В generate параметр --key-color используется с --transparent.")
    source = args.output.with_name(f"{args.output.stem}.source.png")
    if key_color is not None:
        require_new(source)

    text = args.prompt_file.read_text(encoding="utf-8-sig") if args.prompt_file else args.prompt
    prompt = make_prompt(text, key_color)
    image, original = request_image(prompt, args.size)
    if key_color is not None:
        write_new(source, original if image.format == "PNG" else encode_image(image, "PNG"))
        print(f"Исходник: {source.resolve()}")
        image = remove_screen(image, key_color)
    write_new(args.output, encode_image(image, fmt))


def cutout(args: argparse.Namespace) -> None:
    output_format(args.output, transparent=True)
    require_new(args.output)
    try:
        with Image.open(args.input) as image:
            result = remove_screen(image, args.key_color)
    except (UnidentifiedImageError, Image.DecompressionBombError):
        raise ImagenError("Не удалось открыть исходное изображение.") from None
    write_new(args.output, encode_image(result, "PNG"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Изображения Alice AI ART и удаление хромакея.")
    commands = parser.add_subparsers(dest="command", required=True)
    generation = commands.add_parser("generate", help="Сгенерировать изображение по тексту.")
    prompt = generation.add_mutually_exclusive_group(required=True)
    prompt.add_argument("--prompt")
    prompt.add_argument("--prompt-file", type=Path)
    generation.add_argument("--output", type=Path, required=True)
    generation.add_argument("--size", choices=SIZES, default="1024x1024")
    generation.add_argument("--transparent", action="store_true")
    generation.add_argument("--key-color", choices=KEY_COLORS)
    generation.set_defaults(run=generate)

    removal = commands.add_parser("cutout", help="Локально удалить фон с хромакеем.")
    removal.add_argument("--input", type=Path, required=True)
    removal.add_argument("--output", type=Path, required=True)
    removal.add_argument("--key-color", choices=KEY_COLORS, default="green")
    removal.set_defaults(run=cutout)

    args = parser.parse_args(argv)
    try:
        args.run(args)
    except (ImagenError, OSError, UnicodeError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
