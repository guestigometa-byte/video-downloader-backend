# Universal Video Downloader - Backend Setup

This backend is what makes "paste any video URL, get the video" actually work.
The current Netlify site is only a frontend (HTML in the browser). A browser
alone cannot pull a video out of a YouTube / TikTok / Instagram / Pinterest
watch page - that extraction has to happen on a server. That is why the
current site shows a guide instead of downloading watch pages.

## How it works
1. User pastes a URL on the frontend.
2. Frontend calls this backend: `GET /api/info?url=...`
3. Backend uses yt-dlp to find the video file for that page.
4. Frontend calls `GET /api/download?url=...` and the browser downloads the file.

Frontend change needed: set `BACKEND_URL` in the frontend to your deployed
backend URL, for example `https://your-backend.onrender.com`, and change the
Download button to call `/api/download` instead of downloading the pasted
URL directly. The current Netlify frontend does not have this wired in yet -
that wiring is the next step after the backend is live.

## What you need to deploy it
- A server, not Netlify static hosting. Examples: a small VPS, Render,
  Railway, or any host that runs Python.
- Python 3.10+, ffmpeg installed on the server (`apt install ffmpeg` on Ubuntu).
- `pip install -r requirements.txt`, then run `python app.py` (or use gunicorn
  in production, behind HTTPS).

## Cost and maintenance - read this before going live
- Bandwidth and CPU: every download goes through YOUR server, so a popular
  video can use a lot of bandwidth and disk. Start with a small VPS and a
  file-size limit (already set to 500 MB in app.py).
- Breaking changes: YouTube, TikTok, Instagram and Pinterest change their
  pages often. yt-dlp has to be updated regularly (`pip install -U yt-dlp`),
  otherwise downloads start failing.
- Platform terms and copyright: these platforms do not allow downloading
  other people's videos through third-party tools, except where they give
  a download button. A public site that downloads other creators' videos
  risks DMCA complaints, hosting suspension, IP blocks, and AdSense
  rejection. That risk is why the first version was built as a safe,
  guide-only site. Use this backend only for videos you own, have permission
  for, or that are public-domain / Creative Commons with a licence that
  allows downloading, unless you consciously accept the risk above.
- AdSense: do not expect AdSense approval for a site whose main job is
  downloading other people's platform videos. If earning is the goal, the
  safe direct-file tool is the AdSense-friendly version; the universal
  backend version is a traffic tool with a much harder monetisation path.

## Local test (before paying for a server)
```
pip install -r requirements.txt
python app.py
curl "http://localhost:5000/api/info?url=https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
```
Replace YOUR_VIDEO_ID with a video you own or have permission to test with.
