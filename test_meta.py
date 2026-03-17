import os
import glob
from meta_uploader import upload_to_facebook_browser

# Find the most recent video in the output directory
files = glob.glob('output/*.mp4')
if not files:
    print("No mp4 files found in 'output/' to test.")
    exit(1)
    
latest_file = max(files, key=os.path.getctime)
print(f"Testing Meta upload with: {latest_file}")

caption = "Verification Test: #automation #test"
upload_to_facebook_browser(latest_file, caption)
