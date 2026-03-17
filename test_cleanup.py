import os
import glob
import time as time_module

# Manual trigger for the cleanup logic
now = time_module.time()

print("Starting filesystem cleanup test...")

# 1. Clean up heavy intermediate files
patterns = ["output/veo_hook.mp4", "output/narration.wav", "output/narration.srt", "output/nano_banana_fill_*.jpg"]
for pattern in patterns:
    for f in glob.glob(pattern):
        try:
            os.remove(f)
            print(f"Removed intermediate: {f}")
        except Exception as e:
            print(f"Error removing {f}: {e}")

# 2. Keep final mp4s less than 2 days old
for f in os.listdir("output"):
    f_path = os.path.join("output", f)
    if f.endswith(".mp4") and os.path.isfile(f_path):
        if os.stat(f_path).st_mtime < now - (2 * 86400):
            try:
                os.remove(f_path)
                print(f"Removed aged output: {f}")
            except Exception as e:
                print(f"Error removing {f}: {e}")

print("Cleanup validation complete.")
