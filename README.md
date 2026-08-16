# Image Bed - GitHub + jsDelivr CDN

This repository is used as an image hosting service for Claude Telegram Bot.

## Usage

Images uploaded to this repository are accessible via jsDelivr CDN:

```
https://cdn.jsdelivr.net/gh/Frank2T/image-bed@main/images/{filename}
```

## Structure

- `/images` - Uploaded images (organized by date)
- `/temp` - Temporary images (auto-cleanup after 7 days)

## API

Use the `github_image_bed.py` script to upload images:

```bash
python github_image_bed.py upload /path/to/image.jpg
```

Returns the jsDelivr CDN URL.
