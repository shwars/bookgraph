import base64
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import httpx
from openai import OpenAI
from PIL import Image, ImageDraw

import imagen_yart


SCREENS = {"green": (0, 255, 0), "magenta": (255, 0, 255)}
FOLDER = "fake-folder"
KEY = "fake-api-key-for-test"
DOTENV = f'\ufefffolder_id={FOLDER}\r\napi_key="{KEY}"\r\n'.encode("utf-8")


def keyed_image(color):
    screen = SCREENS[color]
    subject = (240, 240, 240)
    image = Image.new("RGB", (96, 72), screen)
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 12, 75, 60), fill=subject)
    draw.rectangle((40, 25, 55, 48), fill=screen)
    draw.ellipse((10, 58, 85, 65), fill=tuple(value * 2 // 3 for value in screen))
    image.putpixel((19, 35), tuple(round((a + b) / 2) for a, b in zip(subject, screen)))
    return image


class CutoutTest(unittest.TestCase):
    def test_both_screens_preserve_light_details_and_remove_spill(self):
        for color in SCREENS:
            with self.subTest(color=color):
                image = keyed_image(color)
                result = imagen_yart.remove_screen(image, color)
                self.assertEqual(result.size, image.size)
                self.assertEqual(result.mode, "RGBA")
                self.assertEqual(result.getpixel((0, 0)), (0, 0, 0, 0))
                self.assertEqual(result.getpixel((44, 30)), (0, 0, 0, 0))
                self.assertEqual(result.getpixel((44, 64)), (0, 0, 0, 0))
                self.assertEqual(result.getpixel((25, 30)), (240, 240, 240, 255))
                red, green, blue, alpha = result.getpixel((19, 35))
                self.assertLess(max(red, green, blue) - min(red, green, blue), 15)
                self.assertLess(abs(alpha - 128), 12)

    def test_rejects_wrong_screen_empty_canvas_and_existing_alpha(self):
        for image in (
            keyed_image("magenta"),
            Image.new("RGB", (20, 20), SCREENS["green"]),
            Image.new("RGBA", (20, 20), (*SCREENS["green"], 128)),
        ):
            with self.subTest(mode=image.mode, size=image.size):
                with self.assertRaises(imagen_yart.ImagenError):
                    imagen_yart.remove_screen(image, "green")

    def test_runs_offline_from_another_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            keyed_image("green").save(base / "input.png")
            result = subprocess.run(
                [sys.executable, "-X", "utf8", str(Path(imagen_yart.__file__).resolve()),
                 "cutout", "--input", "input.png", "--output", "out.png"],
                cwd=base, capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with Image.open(base / "out.png") as output:
                self.assertEqual(output.getchannel("A").getextrema(), (0, 255))


class GenerationTest(unittest.TestCase):
    def test_generation_contract_ordinary_and_transparent(self):
        source = imagen_yart.encode_image(keyed_image("magenta"), "PNG")
        payload = base64.b64encode(source).decode("ascii")
        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(200, json={"created": 1, "data": [{"b64_json": payload}]})

        def mock_client(**kwargs):
            self.assertEqual(kwargs["max_retries"], 0)
            return OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(respond)))

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "prompt.txt").write_text("Медный фонарь", encoding="utf-8")
            with (
                patch.object(imagen_yart, "urlopen", side_effect=lambda *a, **kw: io.BytesIO(DOTENV)) as download,
                patch("openai.OpenAI", side_effect=mock_client),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(imagen_yart.main([
                    "generate", "--prompt-file", str(base / "prompt.txt"), "--size", "1536x1024",
                    "--output", str(base / "lantern.jpeg"),
                ]), 0)
                self.assertEqual(imagen_yart.main([
                    "generate", "--prompt", "Медный фонарь", "--transparent", "--key-color", "magenta",
                    "--output", str(base / "lantern.png"),
                ]), 0)
            with Image.open(base / "lantern.jpeg") as ordinary, Image.open(base / "lantern.png") as sprite:
                self.assertEqual(ordinary.format, "JPEG")
                self.assertEqual(sprite.mode, "RGBA")
                self.assertEqual(sprite.getchannel("A").getextrema(), (0, 255))
            self.assertEqual((base / "lantern.source.png").read_bytes(), source)

        self.assertEqual(download.call_count, 2)
        download.assert_called_with(imagen_yart.CREDENTIALS_URL, timeout=20)
        self.assertEqual(len(requests), 2)
        for request in requests:
            self.assertEqual(str(request.url), f"{imagen_yart.API_URL}/images/generations")
            self.assertEqual(request.headers["authorization"], f"Bearer {KEY}")
            self.assertEqual(request.headers["openai-project"], FOLDER)
        self.assertEqual(json.loads(requests[0].content), {
            "model": f"art://{FOLDER}/aliceai-image-art-3.0", "prompt": "Медный фонарь", "size": "1536x1024",
        })
        self.assertIn("#FF00FF", json.loads(requests[1].content)["prompt"])

    def test_rejects_long_prompt_and_existing_output_before_network(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out.png"
            with patch.object(imagen_yart, "urlopen") as download, redirect_stderr(io.StringIO()):
                self.assertEqual(imagen_yart.main([
                    "generate", "--prompt", "x" * 500, "--transparent", "--output", str(output),
                ]), 1)
                output.write_bytes(b"existing")
                self.assertEqual(imagen_yart.main([
                    "generate", "--prompt", "x", "--output", str(output),
                ]), 1)
                download.assert_not_called()
            self.assertEqual(output.read_bytes(), b"existing")

    def test_keeps_source_on_failed_cutout(self):
        image = Image.new("RGB", (20, 20), "gray")
        source = imagen_yart.encode_image(image, "PNG")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out.png"
            with (
                patch.object(imagen_yart, "request_image", return_value=(image, source)),
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(imagen_yart.main([
                    "generate", "--prompt", "x", "--transparent", "--output", str(output),
                ]), 1)
            self.assertFalse(output.exists())
            self.assertEqual(output.with_name("out.source.png").read_bytes(), source)

    def test_api_error_redacts_response(self):
        def respond(request):
            return httpx.Response(401, json={"error": {"message": KEY}})

        def mock_client(**kwargs):
            return OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(respond)))

        with (
            patch.object(imagen_yart, "urlopen", return_value=io.BytesIO(DOTENV)),
            patch("openai.OpenAI", side_effect=mock_client),
        ):
            with self.assertRaisesRegex(imagen_yart.ImagenError, "HTTP 401") as error:
                imagen_yart.request_image("Тест", "1024x1024")
            self.assertNotIn(KEY, str(error.exception))

    def test_bad_credentials_and_download_error_are_safe(self):
        for download, message in (
            ({"return_value": io.BytesIO(f"api_key={KEY}".encode())}, "folder_id"),
            ({"side_effect": HTTPError(imagen_yart.CREDENTIALS_URL, 403, KEY, {}, None)}, "HTTP 403"),
        ):
            with self.subTest(message=message), patch.object(imagen_yart, "urlopen", **download):
                with self.assertRaisesRegex(imagen_yart.ImagenError, message) as error:
                    imagen_yart.read_credentials()
                self.assertNotIn(KEY, str(error.exception))


if __name__ == "__main__":
    unittest.main()
