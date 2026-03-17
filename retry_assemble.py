import time
import os
import glob
from main import assemble_video
from youtube_uploader import get_authenticated_service, upload_video

# Paths for intermediate assets in the output folder
veo = "output/veo_hook.mp4"
imgs = sorted(glob.glob("output/nano_banana_fill_*.jpg"))
aud = "output/narration.wav"
srt = "output/narration.srt"
out = f"output/final_fixed_{int(time.time())}.mp4"

if not os.path.exists(veo) or not imgs or not os.path.exists(aud):
    print("Error: Missing required intermediate assets in 'output/'.")
    exit(1)

print(f"Re-assembling video with {len(imgs)} images...")
assemble_video(veo, imgs, aud, out, srt)

print("Starting YouTube Upload...")
youtube = get_authenticated_service()
# Note: Update these metadata fields if retrying for a specific topic
title = "Historical Innovation Update"
desc = "Automated upload retry. #history #innovation #shorts"

upload_video(youtube, out, title, desc)
print(f"Success! Final video saved to {out}")
