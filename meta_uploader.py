import logging
import os
import sys
import time
from playwright.sync_api import sync_playwright

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

def upload_to_facebook_browser(file_path: str, caption: str) -> bool:
    """Uploads a video to Facebook Reels using browser automation."""
    logging.info(f"Starting headless Facebook upload for {file_path}")
    
    # Path to store session state so we don't have to login every time
    state_file = "fb_state.json"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) # Run headless for automation
        
        # Load state if it exists
        if os.path.exists(state_file):
            logging.info("Loading existing Facebook session...")
            context = browser.new_context(storage_state=state_file)
        else:
            logging.info("No session found. Creating a new one...")
            context = browser.new_context()

        page = context.new_page()
        
        # Go to Facebook
        logging.info("Navigating to Facebook...")
        page.goto("https://www.facebook.com/")
        
        # Check if we need to login
        if page.query_selector('input[name="email"]'):
            logging.warning("NOT LOGGED IN. Please log in to Facebook manually in the browser window.")
            logging.warning("Once logged in and on the homepage, return here and press ENTER.")
            input("Press ENTER to continue after logging in...")
            
            # Save state for future runs
            context.storage_state(path=state_file)
            logging.info("Session saved for future headless runs.")
            
        logging.info("Navigating to Reels creation page...")
        page.goto("https://www.facebook.com/reels/create")
        time.sleep(5) # Wait for page to fully render
        
        try:
            # Look for the file input element (it's usually hidden)
            # Facebook puts multiple hidden file inputs on the page, so we grab the first one
            file_input = page.locator('input[type="file"][accept*="video"]').first
            
            if not file_input.is_visible():
                logging.info("File input hidden, attempting to set files anyway...")
                
            file_input.set_input_files(file_path)
            logging.info("File selected. Waiting for upload to process...")
            
            time.sleep(30) # Wait for initial processing
            
            # Click "Next" through the trim/crop screens until we hit the final page
            while True:
                next_btn = page.get_by_role("button", name="Next")
                post_btn = page.get_by_role("button", name="Post")
                
                if post_btn.count() > 0 and post_btn.first.is_visible():
                    logging.info("Reached the final Reel settings screen.")
                    break
                elif next_btn.count() > 0 and next_btn.first.is_visible():
                    logging.info("Clicking Next...")
                    next_btn.first.click()
                    time.sleep(5)
                else:
                    logging.info("No Next or Post buttons found, waiting...")
                    time.sleep(3)
                    
            # We are on the final screen. Type the caption
            caption_box = page.get_by_role("textbox", name="Describe your reel...")
            if caption_box.count() == 0:
                 caption_box = page.locator('div[contenteditable="true"][role="textbox"]').first
                 
            if caption_box.count() > 0:
                caption_box.click()
                caption_box.fill(caption)
                logging.info("Caption added.")
            else:
                 logging.warning("Could not find caption box, skipping caption.")
            
            # Click Post
            # Specifically target the primary blue button at the bottom of the form
            post_btn = page.locator('div[role="button"]:has-text("Post")').last
            if post_btn.count() > 0:
                post_btn.click()
                logging.info("Post button clicked! Waiting for finalization... Do NOT close the browser!")
                # Facebook takes a LONG time to actually process and finalize the video after clicking Post.
                # If we close the browser context too early, the upload is abandoned.
                time.sleep(60) 
                logging.info("Assuming upload is complete.")
                return True
            else:
                logging.error("Could not find the Post button.")
                return False
                
        except Exception as e:
             logging.error(f"Browser automation failed: {e}")
             return False
        finally:
             browser.close()

def upload_to_meta(file_path: str, title: str, description: str, platform: str = "facebook") -> None:
    """Main entry point for Meta uploads (Currently supports Facebook via Playwright)."""
    full_caption = f"{title}\n\n{description}"
        
    if platform in ["facebook", "both"]:
        upload_to_facebook_browser(file_path, full_caption)
        
if __name__ == "__main__":
    pass
