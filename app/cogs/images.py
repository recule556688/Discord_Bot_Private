"""Image context menus: add text, emoji, sticker."""

import io
import os
import random
import re
import string

import discord
import requests
from PIL import Image, ImageDraw, ImageFont, ImageSequence
from discord import app_commands

def find_urls_in_string(s):
    # Simple, robust URL pattern (avoids regex errors from complex patterns)
    regex = r"https?://[^\s<>\"']+|www\.[^\s<>\"']+"
    urls = re.findall(regex, s, re.IGNORECASE)
    return urls


def get_fitting_font(text, image, draw, font_path):
    """Get font that fits the image, scaling dynamically with image size."""
    min_dim = min(image.size[0], image.size[1])
    # Base size: ~15% of smaller dimension (scales with image)
    base_font_size = max(60, int(min_dim * 0.15))
    base_font_size = min(280, base_font_size)  # Cap for very large images
    min_font_size = max(24, int(min_dim * 0.05))  # Min ~5% of dimension

    font_size = base_font_size
    font = ImageFont.truetype(font_path, font_size)
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Allow text up to 90% width and 50% height
    while (
        text_width > image.size[0] * 0.9 or text_height > image.size[1] * 0.5
    ) and font_size > min_font_size:
        font_size -= 1
        font = ImageFont.truetype(font_path, font_size)
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

    return font, text_width, text_height


async def process_attachment(interaction, attachment, text):
    try:
        response = requests.get(
            attachment.url, timeout=15, headers=_IMAGE_HEADERS
        )
        if response.status_code != 200:
            await interaction.followup.send(
                f"Failed to download content, status code: {response.status_code}",
                ephemeral=True,
            )
            return

        if attachment.content_type == "image/gif":
            gif_bytes = io.BytesIO(response.content)
            await process_gif(interaction, gif_bytes, text)
        else:
            image_bytes = io.BytesIO(response.content)
            await process_image(interaction, image_bytes, text)
    except Exception as e:
        await interaction.followup.send(
            f"An error occurred while processing the attachment: {e}",
            ephemeral=True,
        )


# Headers for fetching images (Discord CDN and some providers require these)
_IMAGE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": "https://discord.com/",
}


async def process_image_url(interaction, url, text, is_gif=False):
    """Fetch URL and process image/GIF. Raises on failure (caller can try next URL)."""
    response = requests.get(
        url, timeout=15, headers=_IMAGE_HEADERS, stream=True
    )
    response.raise_for_status()
    content = response.content

    # Validate we got image data (some URLs return HTML error pages)
    if not content or len(content) < 100:
        raise ValueError("URL did not return valid image data")

    # Auto-detect GIF from Content-Type (Discord CDN doesn't always have .gif in URL)
    content_type = response.headers.get("Content-Type", "").lower()
    if "gif" in content_type:
        is_gif = True

    image_bytes = io.BytesIO(content)
    if is_gif:
        await process_gif(interaction, image_bytes, text)
    else:
        await process_image(interaction, image_bytes, text)


async def process_image(interaction, image_bytes, text):
    try:
        img = Image.open(image_bytes)
    except Exception as e:
        await interaction.followup.send(
            "Could not open image. The URL may not point to a valid image file.",
            ephemeral=True,
        )
        return

    with img:
        draw = ImageDraw.Draw(img)
        font_path = os.path.join(os.getcwd(), "data", "Roboto-Bold.ttf")
        font, text_width, text_height = get_fitting_font(
            text, img, draw, font_path
        )
        x = (img.width - text_width) / 2
        y = (img.height - text_height) / 2
        draw.text((x, y), text, fill="white", font=font)

        output_buffer = io.BytesIO()
        img.save(output_buffer, format="PNG")
        output_buffer.seek(0)
        await interaction.followup.send(
            file=discord.File(fp=output_buffer, filename="edited_image.png")
        )


async def process_gif(interaction, gif_bytes, text):
    try:
        with Image.open(gif_bytes) as img:
            if img.format != "GIF":
                raise ValueError("Not a valid GIF format")

            # RGBA images only support Fast Octree (2) or libimagequant (3).
            # Use Fast Octree - no extra deps, good quality with FLOYDSTEINBERG dithering.
            try:
                method = Image.Quantize.FASTOCTREE
                dither = Image.Dither.FLOYDSTEINBERG
            except AttributeError:
                method = Image.FASTOCTREE
                dither = Image.FLOYDSTEINBERG

            frames = []
            durations = []
            disposals = []
            for frame in ImageSequence.Iterator(img):
                duration = frame.info.get("duration", img.info.get("duration", 100))
                disposal = frame.info.get("disposal", 2)
                frame = frame.convert("RGBA")
                draw = ImageDraw.Draw(frame)
                font_path = os.path.join(os.getcwd(), "data", "Roboto-Bold.ttf")
                font, text_width, text_height = get_fitting_font(
                    text, frame, draw, font_path
                )
                x = (frame.width - text_width) / 2
                y = (frame.height - text_height) / 2
                draw.text((x, y), text, fill="white", font=font)
                frames.append(frame.copy())
                durations.append(duration)
                disposals.append(disposal)

            # quantize(palette=...) requires RGB or L mode, not RGBA
            def to_rgb(f):
                if f.mode == "RGBA":
                    rgb = Image.new("RGB", f.size, (255, 255, 255))
                    rgb.paste(f, mask=f.split()[3])
                    return rgb
                return f.convert("RGB")

            rgb_frames = [to_rgb(f) for f in frames]

            # Quantize with Fast Octree palette + FLOYDSTEINBERG dithering
            # Use consistent palette across all frames to avoid flickering
            first_quantized = rgb_frames[0].quantize(
                colors=256, method=method, dither=dither
            )
            quantized_frames = [first_quantized]
            for frame in rgb_frames[1:]:
                qf = frame.quantize(palette=first_quantized, dither=dither)
                quantized_frames.append(qf)

            output_buffer = io.BytesIO()
            quantized_frames[0].save(
                output_buffer,
                format="GIF",
                save_all=True,
                append_images=quantized_frames[1:],
                duration=durations,
                loop=img.info.get("loop", 0),
                disposal=disposals,
                optimize=False,
            )
            output_buffer.seek(0)

            await interaction.followup.send(
                file=discord.File(fp=output_buffer, filename="edited_image.gif")
            )
    except Exception as e:
        await interaction.followup.send(
            f"An error occurred while processing the GIF: {e}", ephemeral=True
        )


async def process_sticker(interaction, sticker, text):
    try:
        sticker_url = sticker.url if hasattr(sticker, "url") else sticker.image_url
        response = requests.get(
            sticker_url, timeout=15, headers=_IMAGE_HEADERS
        )
        sticker_bytes = io.BytesIO(response.content)
        await process_image(interaction, sticker_bytes, text)
    except Exception as e:
        await interaction.followup.send(
            f"An error occurred while processing the sticker: {e}",
            ephemeral=True,
        )


def _get_urls_from_embeds(message):
    """Extract image/GIF URLs from Discord embeds (GIF picker, link previews)."""
    urls = []
    for embed in message.embeds:
        # Prefer direct image URLs (proxy_url is Discord's cached version)
        if embed.image:
            url = getattr(embed.image, "proxy_url", None) or embed.image.url
            if url and url not in urls:
                urls.append(url)
        if embed.thumbnail:
            url = getattr(embed.thumbnail, "proxy_url", None) or embed.thumbnail.url
            if url and url not in urls:
                urls.append(url)
        if embed.video and embed.video.url:
            urls.append(embed.video.url)
        if embed.url and embed.url not in urls:
            urls.append(embed.url)
    return urls


async def _process_url(interaction, url, text):
    """Process a single URL (direct GIF or image). Returns True on success."""
    try:
        if url.lower().endswith(".gif"):
            await process_image_url(interaction, url, text, is_gif=True)
            return True
        await process_image_url(interaction, url, text)
        return True
    except (requests.RequestException, ValueError, Exception):
        # URL failed (404, invalid data, etc.) - caller can try next URL
        return False


async def add_text_to_image(interaction, message, text):
    await interaction.response.defer()

    if message.attachments:
        attachment = message.attachments[0]
        if (
            attachment.content_type.startswith("image/")
            or attachment.content_type == "image/gif"
        ):
            await process_attachment(interaction, attachment, text)
        else:
            await interaction.followup.send(
                "Unsupported file type. Please upload an image or GIF.",
                ephemeral=True,
            )
    elif message.embeds:
        # GIF from Discord picker or link preview
        urls = _get_urls_from_embeds(message)
        processed = False
        for url in urls:
            if await _process_url(interaction, url, text):
                processed = True
                break
        if not processed:
            await interaction.followup.send(
                "Could not download the image or GIF (URL may be expired or unavailable).",
                ephemeral=True,
            )
    elif message.content:
        urls = find_urls_in_string(message.content)
        if urls:
            processed = False
            for url in urls:
                if await _process_url(interaction, url, text):
                    processed = True
                    break
            if not processed:
                await interaction.followup.send(
                    "Could not download the image or GIF from the URL.",
                    ephemeral=True,
                )
        else:
            await interaction.followup.send(
                "No valid content found (image, GIF, or URL).", ephemeral=True
            )
    elif message.stickers:
        await process_sticker(interaction, message.stickers[0], text)
    else:
        await interaction.followup.send(
            "No valid content found (image, GIF, sticker, or URL).",
            ephemeral=True,
        )


# Context menus must be defined at module level (discord.py limitation)
@app_commands.context_menu(name="Gay to Gay")
async def gay_to_gay(
    interaction: discord.Interaction, message: discord.Message
):
    await add_text_to_image(interaction, message, "Gay")


@app_commands.context_menu(name="Ratio to Ratio")
async def ratio_to_ratio(
    interaction: discord.Interaction, message: discord.Message
):
    await add_text_to_image(
        interaction, message, "Ratio + don't care + didn't ask"
    )


@app_commands.context_menu(name="Féminisme to Féminisme")
async def feminisme_to_feminisme(
    interaction: discord.Interaction, message: discord.Message
):
    await add_text_to_image(
        interaction, message, "Femme + Féministe + Féminisme\n+ Blue haired dragon"
    )


@app_commands.context_menu(name="Image to emoji")
async def image_to_emoji(
    interaction: discord.Interaction, message: discord.Message
):
    if message.attachments:
        attachment = message.attachments[0]
        if attachment.content_type.startswith("image/"):
            await interaction.response.defer(ephemeral=True)
            response = requests.get(attachment.url, headers=_IMAGE_HEADERS)
            image_bytes = io.BytesIO(response.content)

            with Image.open(image_bytes) as img:
                img.thumbnail((128, 128), Image.LANCZOS)
                output_buffer = io.BytesIO()
                img.save(output_buffer, format="PNG", optimize=True)
                output_buffer.seek(0)

                if output_buffer.getbuffer().nbytes > 256 * 1024:
                    await interaction.followup.send(
                        "Image is too large to be uploaded as an emoji (must be under 256 KB).",
                        ephemeral=True,
                    )
                    return

                output_buffer.seek(0)
                guild = interaction.guild
                if guild is None:
                    # DM: can't create server emoji, send resized image instead
                    await interaction.followup.send(
                        "Emoji creation only works in servers. Here's your resized image (128×128):",
                        file=discord.File(
                            fp=output_buffer, filename="emoji_preview.png"
                        ),
                        ephemeral=True,
                    )
                else:
                    try:
                        emoji = await guild.create_custom_emoji(
                            name="".join(
                                random.choices(
                                    string.ascii_letters + string.digits, k=5
                                )
                            ),
                            image=output_buffer.read(),
                        )
                        await interaction.followup.send(
                            f"Emoji created successfully: <:{emoji.name}:{emoji.id}>",
                            ephemeral=True,
                        )
                    except discord.HTTPException as e:
                        await interaction.followup.send(
                            f"Failed to create emoji: {e}", ephemeral=True
                        )
        else:
            await interaction.response.send_message(
                "The attachment is not an image.", ephemeral=True
            )
    else:
        await interaction.response.send_message(
            "No attachment found in the message.", ephemeral=True
        )


@app_commands.context_menu(name="Image to Sticker")
async def image_to_sticker(
    interaction: discord.Interaction, message: discord.Message
):
    if message.attachments:
        attachment = message.attachments[0]
        if attachment.content_type.startswith("image/"):
            response = requests.get(
                attachment.url, timeout=15, headers=_IMAGE_HEADERS
            )
            image_bytes = io.BytesIO(response.content)

            with Image.open(image_bytes) as img:
                output_buffer = io.BytesIO()
                img.save(output_buffer, format="PNG", optimize=True)
                output_buffer.seek(0)

                if output_buffer.getbuffer().nbytes > 512 * 1024:
                    quality = 85
                    while (
                        output_buffer.getbuffer().nbytes > 512 * 1024
                        and quality > 10
                    ):
                        output_buffer = io.BytesIO()
                        img.convert("RGB").save(
                            output_buffer,
                            format="JPEG",
                            quality=quality,
                            optimize=True,
                        )
                        output_buffer.seek(0)
                        quality -= 5

                await interaction.response.send_message(
                    file=discord.File(
                        fp=output_buffer, filename="resized_image.png"
                    )
                )
        else:
            await interaction.response.send_message(
                "The attachment is not an image.", ephemeral=True
            )
    else:
        await interaction.response.send_message(
            "No attachment found in the message.", ephemeral=True
        )


async def setup(bot):
    bot.tree.add_command(gay_to_gay)
    bot.tree.add_command(ratio_to_ratio)
    bot.tree.add_command(feminisme_to_feminisme)
    bot.tree.add_command(image_to_emoji)
    bot.tree.add_command(image_to_sticker)
