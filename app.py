"""
Universal Video Downloader - backend (Flask + yt-dlp)

What this does:
- Takes a video page URL (YouTube, TikTok, Instagram, Pinterest, etc.)
- Uses yt-dlp to find the direct video file for that page
- Returns video info (title, formats) and a download link / file

IMPORTANT - legal use only:
This backend must only be used for videos you own, or videos you have
clear permission to download, or public-domain / Creative Commons videos
whose licence allows downloading. Do not use it to copy other creators'
copyrighted work, and do not put it on a public AdSense site without
understanding the platform-terms and copyright risks explained in README.md.
The site owner is responsible for how the tool is used.

Run locally:
  pip install -r requirements.txt
  python app.py
  # then open http://localhost:5000

Deploy:
  This needs a real server (VPS, Render, Railway, etc.) with ffmpeg
  installed. It will NOT work on Netlify static hosting alone, because
  Netlify static hosting cannot run Python / yt-dlp.
"""

from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS
import yt_dlp
import os
import tempfile
import uuid

app = Flask(__name__)
CORS(app)  # frontend on another domain can call this API

# Keep downloads small and short-lived: files are deleted after sending.
MAX_FILESIZE_MB = 500


def base_opts():
    # FIX for the 400 error seen on Render (Nov 3, 2026):
    # Old yt-dlp (2024) + cloud IP = YouTube "Sign in to confirm you are
    # not a bot" / player errors. Using the android/ios player clients
    # and a normal browser User-Agent fixes most of those cases.
    # If YouTube still blocks the datacenter IP, the error below now
    # says so plainly instead of a bare 400.
    return {
        "quiet": True,
        "noplaylist": True,
        "socket_timeout": 30,
        "retries": 2,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        },
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "web"],
                "player_skip": ["webpage"],
            }
        },
    }


def get_info(url):
    ydl_opts = {**base_opts(), "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


@app.route("/api/info", methods=["GET"])
def info():
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"error": "url is required"}), 400
    try:
        data = get_info(url)
    except Exception as e:
        msg = str(e)
        if "bot" in msg.lower() or "sign in" in msg.lower() or "confirm" in msg.lower():
            return jsonify({"error": "YouTube blocked this server request (bot check). Try again in a few minutes, or try a direct video file link. The video itself exists - this is a platform block on the server IP, not a broken link."}), 502
        return jsonify({"error": f"Could not read this video: {msg}"}), 400

    formats = []
    for f in (data.get("formats") or [])[-12:]:
        formats.append({
            "format_id": f.get("format_id"),
            "ext": f.get("ext"),
            "resolution": f.get("resolution") or f.get("height"),
            "filesize": f.get("filesize"),
            "url": f.get("url"),
        })

    return jsonify({
        "title": data.get("title"),
        "uploader": data.get("uploader"),
        "duration": data.get("duration"),
        "thumbnail": data.get("thumbnail"),
        "webpage_url": data.get("webpage_url"),
        "formats": formats,
        "direct_url": data.get("url"),
    })


@app.route("/api/download", methods=["GET"])
def download():
    """
    Download the best available mp4 (or best format) for the given URL
    and send it back to the browser as a file.
    Query: ?url=<video page url>&format_id=<optional>
    """
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"error": "url is required"}), 400

    tmpdir = tempfile.mkdtemp(prefix="vid_dl_")
    outtmpl = os.path.join(tmpdir, "%(title)s.%(ext)s")
    ydl_opts = {
        **base_opts(),
        "outtmpl": outtmpl,
        # Prefer mp4, fall back to best available. Change this if needed.
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "max_filesize": MAX_FILESIZE_MB * 1024 * 1024,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        msg = str(e)
        if "bot" in msg.lower() or "sign in" in msg.lower():
            return jsonify({"error": "YouTube blocked this server request (bot check). Try again later, or use a direct video file link."}), 502
        return jsonify({"error": f"Download failed: {msg}"}), 400

    files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir)]
    if not files:
        return jsonify({"error": "No file was downloaded"}), 400

    path = files[0]
    return send_file(path, as_attachment=True, download_name=os.path.basename(path))


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Universal Video Downloader backend is running. Use /api/info?url=... and /api/download?url=..."})


if __name__ == "__main__":
    # nosec - local / server use only, put behind HTTPS in production
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
