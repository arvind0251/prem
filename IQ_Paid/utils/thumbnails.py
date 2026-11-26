import asyncio
import os
import re
import textwrap
import numpy as np
import aiofiles
import aiohttp
from PIL import (
    Image,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
)
from py_yt import VideosSearch
from config import YOUTUBE_IMG_URL
def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    ratio = min(widthRatio, heightRatio)
    newWidth = int(image.size[0] * ratio)
    newHeight = int(image.size[1] * ratio)
    try:
        resample = Image.Resampling.LANCZOS
    except AttributeError:
        resample = Image.ANTIALIAS  # For Pillow<10
    image = image.resize((newWidth, newHeight), resample)
    return image
def get_dominant_color(image):
    """Extract the dominant color from the image"""
    # Convert to RGB if not already
    image = image.convert('RGB')
    
    # Resize to speed up processing
    image = image.resize((50, 50))
    
    # Get all pixels
    pixels = np.array(image)
    
    # Reshape to get list of RGB values
    pixel_list = pixels.reshape(-1, 3)
    
    # Calculate average color
    avg_color = tuple(pixel_list.mean(axis=0).astype(int))
    
    # Ensure color is bright enough for visibility
    # If too dark, brighten it
    if sum(avg_color) < 200:  # If color is too dark
        brightened = tuple(min(255, int(c * 1.5)) for c in avg_color)
        return brightened
    
    return avg_color
def get_contrasting_color(bg_color):
    """Get a contrasting color for better visibility"""
    # Calculate luminance
    luminance = (0.299 * bg_color[0] + 0.587 * bg_color[1] + 0.114 * bg_color[2])
    
    # Return white for dark backgrounds, dark for light backgrounds
    return (255, 255, 255) if luminance < 128 else (50, 50, 50)
channel_cache = {}

THUMB_URLS = (
    "https://i.ytimg.com/vi/{id}/maxresdefault.jpg",
    "https://i.ytimg.com/vi/{id}/hq720.jpg",
    "https://i.ytimg.com/vi/{id}/hqdefault.jpg",
)


async def _download_thumb(videoid, path):
    timeout = aiohttp.ClientTimeout(total=8)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for template in THUMB_URLS:
            try:
                async with session.get(template.format(id=videoid)) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.read()
                    if len(data) < 2000:
                        continue
                    async with aiofiles.open(path, mode="wb") as f:
                        await f.write(data)
                    return True
            except Exception:
                continue
    return False


_CHANNEL_SEP = re.compile(r"\s*[\u2022\u00b7\u2219\u2027|]\s*|\s+\.\s+")


def _clean_channel(name):
    """'Catchy Beats . 1.4M views . 4 days ago' -> 'Catchy Beats' (keep only the channel part)."""
    if not name:
        return None
    name = str(name).strip()
    first = _CHANNEL_SEP.split(name)[0].strip()
    return first or name


async def _lookup_channel(videoid):
    try:
        result = await asyncio.wait_for(
            VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1).next(),
            timeout=3,
        )
        items = result.get("result") or []
        if items:
            name = _clean_channel((items[0].get("channel") or {}).get("name"))
            if name:
                channel_cache[videoid] = name
    except Exception:
        pass


async def get_thumb(videoid, user_id=None):
    """Plain YouTube thumbnail (like the reference design). Also caches the channel name."""
    os.makedirs("cache", exist_ok=True)
    final_path = f"cache/{videoid}.jpg"
    have_file = os.path.isfile(final_path)
    tasks = []
    if not have_file:
        tasks.append(_download_thumb(videoid, final_path))
    if videoid not in channel_cache:
        tasks.append(_lookup_channel(videoid))
    results = await asyncio.gather(*tasks, return_exceptions=True) if tasks else []
    if not have_file:
        ok = results[0] if results and results[0] is True else False
        if not ok:
            return YOUTUBE_IMG_URL
    return final_path
