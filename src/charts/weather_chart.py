"""
Weather forecast card image generator.

Uses an HTML template + Puppeteer (via Node.js) to render a clean
card-style forecast, much more visually appealing than Matplotlib.
"""

import json
import logging
import os
import subprocess
import tempfile
logger = logging.getLogger(__name__)

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_GENERATE_JS = os.path.join(_SCRIPT_DIR, "generate_card.js")


def generate_weather_chart(
    forecast: list[dict],
    location: str,
    output_path: str | None = None,
) -> str:
    """Generate a weather card image using HTML + Puppeteer.

    Args:
        forecast: List of daily forecast dicts (from DataSource.parse).
        location: City/district name for the card title.
        output_path: Where to save the PNG. If None, uses a temp file.

    Returns:
        Absolute path to the generated PNG image.
    """
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".png", prefix="weather_card_")
        os.close(fd)

    # Build input for the JS script
    input_data = {
        "location": location,
        "source": "Open-Meteo",
        "forecast": [
            {
                "date": d["date"],

                "wx": d.get("wx") or "",
                "max_t": d.get("max_t"),
                "min_t": d.get("min_t"),
                "pop": d.get("pop"),
            }
            for d in forecast
        ],
    }

    # Call the Node.js script
    cmd = [
        "node",
        _GENERATE_JS,
        "--forecast", json.dumps(input_data, ensure_ascii=False),
        "--output", output_path,
    ]

    logger.info("Generating card via Node.js/Puppeteer...")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        logger.error("Card generation failed (exit %d): %s",
                      result.returncode, result.stderr)
        raise RuntimeError(f"Card generation failed: {result.stderr}")

    logger.info("Card saved to %s", output_path)
    return os.path.abspath(output_path)
