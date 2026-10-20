#!/usr/bin/env python3
"""Build a lean, web-ready copy of the site: only referenced assets,
videos re-encoded to H.264 mp4, huge PNGs converted to JPEG/downscaled."""
import re, os, shutil, subprocess, sys
from PIL import Image

SRC = "/sessions/zen-dazzling-cori/mnt/Desktop/sam website"
DST = "/sessions/zen-dazzling-cori/mnt/Desktop/samdiliberto-site"

html = open(os.path.join(SRC, "index.html")).read()
refs = sorted(set(re.findall(r'(?:images|fonts)/[^"`\']+?\.(?:png|jpe?g|gif|webp|mov|mp4|webm|ttf|otf|woff2?)', html, re.I)))
print(f"{len(refs)} referenced assets", flush=True)

os.makedirs(DST, exist_ok=True)
VIDEO = re.compile(r'\.(mov|mp4|webm)$', re.I)
new_html = html
total_before = total_after = 0

for ref in refs:
    src = os.path.join(SRC, ref)
    if not os.path.exists(src):
        print(f"MISSING: {ref}", flush=True); continue
    size = os.path.getsize(src)
    total_before += size
    out_ref = ref
    dst = os.path.join(DST, ref)
    os.makedirs(os.path.dirname(dst), exist_ok=True)

    # resume: skip anything already produced (any candidate output name)
    done = None
    for cand_ref in {ref,
                     re.sub(r'\.(mov|webm|mp4)$', '.mp4', ref, flags=re.I),
                     re.sub(r'\.png$', '.jpg', ref, flags=re.I)}:
        cand = os.path.join(DST, cand_ref)
        if os.path.exists(cand) and os.path.getsize(cand) > 0:
            done = cand_ref; break
    if done:
        if done != ref:
            new_html = new_html.replace(ref, done)
        total_after += os.path.getsize(os.path.join(DST, done))
        continue

    if VIDEO.search(ref):
        out_ref = re.sub(r'\.(mov|webm|mp4)$', '.mp4', ref, flags=re.I)
        dst = os.path.join(DST, out_ref)
        crf = "27" if size > 40e6 else "25"
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", src,
               "-vf", "scale='min(1600,iw)':-2",
               "-c:v", "libx264", "-crf", crf, "-preset", "veryfast",
               "-pix_fmt", "yuv420p", "-movflags", "+faststart",
               "-map", "0:v:0", "-map", "0:a?", "-c:a", "aac", "-b:a", "128k",
               dst]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(dst):
            print(f"FFMPEG FAIL {ref}: {r.stderr[:200]}", flush=True)
            shutil.copy2(src, dst)
    elif ref.lower().endswith(".png") and size > 3e6:
        img = Image.open(src)
        has_alpha = img.mode in ("RGBA", "LA") and img.getextrema()[-1][0] < 255
        if img.width > 2400:
            img = img.resize((2400, round(img.height * 2400 / img.width)), Image.LANCZOS)
        if has_alpha:
            img.save(dst, optimize=True)
        else:
            out_ref = re.sub(r'\.png$', '.jpg', ref, flags=re.I)
            dst = os.path.join(DST, out_ref)
            img.convert("RGB").save(dst, "JPEG", quality=86)
    else:
        shutil.copy2(src, dst)

    if out_ref != ref:
        new_html = new_html.replace(ref, out_ref)
    total_after += os.path.getsize(dst)
    print(f"{size/1e6:6.1f} -> {os.path.getsize(dst)/1e6:6.1f} MB  {out_ref}", flush=True)

open(os.path.join(DST, "index.html"), "w").write(new_html)
print(f"DONE  {total_before/1e6:.0f} MB -> {total_after/1e6:.0f} MB", flush=True)
