import json
import logging
import os
import subprocess
import sys
import time

from google import genai
from google.cloud import texttospeech
from google.genai import types

from youtube_uploader import get_authenticated_service, upload_video
from meta_uploader import upload_to_meta
from ledger import get_recent_topics, log_content

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

def generate_script_and_prompts(client: genai.Client) -> dict:
    """Queries Gemini to generate the historical fact, narration, media prompts, and metadata."""
    logging.info("Generating script and prompts via Gemini API.")
    
    recent_topics = get_recent_topics()
    
    prompt = (
        "Generate an engaging educational or entertaining short-form video script for today. "
        "The content should be optimized for a general audience and focus on fascinating facts, stories, or insights. "
        "CRITICAL INSTRUCTION: You MUST NOT generate a video about any of the following recent topics: " + recent_topics + ". "
        "Return a JSON object with exactly five keys: 'narration' (a 60-word script), "
        "'veo_prompt' (a detailed prompt for an 8-second vertical 9:16 cinematic video visual hook. MUST NOT contain any words that could trigger safety filters. Keep it purely educational, abstract, or visually stunning), "
        "'image_prompts' (a list of exactly THREE detailed prompts for intricate vertical 9:16 visuals, each highlighting a different angle or aspect of the subject), "
        "'title' (a catchy short-form video title under 60 characters), and "
        "'description' (a video description with 3 relevant hashtags)."
    )
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    
    try:
        data = json.loads(response.text)
        return data
    except json.JSONDecodeError:
        logging.error("Failed to parse Gemini JSON response.")
        sys.exit(1)

def generate_veo_video(client: genai.Client, prompt: str, output_path: str) -> None:
    """Generates an 8-second 9:16 video using Veo 3.1 on Vertex AI."""
    logging.info("Starting Veo 3.1 video generation on Vertex AI.")
    model_id = "veo-3.1-generate-preview"
    
    config = types.GenerateVideosConfig(
        aspect_ratio="9:16",
        duration_seconds=8,
    )
    
    operation = client.models.generate_videos(
        model=model_id,
        prompt=prompt,
        config=config,
    )

    while not operation.done:
        time.sleep(10)
        operation = client.operations.get(operation)

    result_obj = getattr(operation, "response", getattr(operation, "result", None))
    
    if not result_obj or not result_obj.generated_videos:
        logging.error(f"Veo video generation failed. Result object: {result_obj}, Operation: {operation}")
        sys.exit(1)

    video_uri = result_obj.generated_videos[0].video.uri
    if not video_uri:
        video_bytes = result_obj.generated_videos[0].video.video_bytes
        if video_bytes:
             with open(output_path, "wb") as f:
                 f.write(video_bytes)
             logging.info(f"Veo video saved to {output_path}.")
             return
        logging.error("Veo response contained no URI or video bytes.")
        sys.exit(1)
        
    logging.info(f"Downloading Veo video from URI: {video_uri}")
    import urllib.request
    urllib.request.urlretrieve(video_uri, output_path)
    logging.info(f"Veo video saved to {output_path}.")

def generate_nano_banana_image(client: genai.Client, prompt: str, output_path: str) -> None:
    """Generates a 9:16 image using Gemini 3 Flash Image via Vertex AI."""
    logging.info("Generating image via GCP Imagen API.")
    
    result = client.models.generate_images(
        model="imagen-3.0-generate-001",
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            output_mime_type="image/jpeg",
            aspect_ratio="9:16",
        ),
    )
    
    if not result.generated_images:
        logging.error("Image generation failed.")
        sys.exit(1)

    with open(output_path, "wb") as f:
        f.write(result.generated_images[0].image.image_bytes)
        
    logging.info(f"Image saved to {output_path}.")

def generate_gcp_audio(text: str, output_path: str) -> None:
    """Generates TTS audio using Google Cloud Text-to-Speech API."""
    logging.info("Generating audio via Google Cloud TTS.")
    
    tts_client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Journey-D" 
    )
    
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16
    )
    
    response = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    
    with open(output_path, "wb") as out:
        out.write(response.audio_content)
        
    logging.info(f"Audio saved to {output_path}.")

import random
import glob

def get_audio_duration(audio_path: str) -> float:
    """Returns the duration of the audio file in seconds."""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as e:
        logging.warning(f"Failed to get audio duration, defaulting to 25s: {e}")
        return 25.0

def generate_subtitles(audio_path: str, output_dir: str) -> str:
    """Generates SRT subtitles using local OpenAI Whisper."""
    logging.info("Generating subtitles with local Whisper model.")
    cmd = [
        sys.executable, "-m", "whisper", audio_path,
        "--model", "base",
        "--output_format", "srt",
        "--output_dir", output_dir
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        srt_path = os.path.join(output_dir, f"{base_name}.srt")
        logging.info(f"Subtitles generated at {srt_path}")
        return srt_path
    except subprocess.CalledProcessError as e:
        logging.error(f"Whisper subtitle generation failed: {e.stderr.decode()}")
        return ""

def assemble_video(
    video_path: str, image_paths: list[str], audio_path: str, output_path: str, subtitle_path: str = ""
) -> None:
    """Stitches the video, multiple images, and audio together using FFmpeg. Includes Ken Burns, crossfades, ambient bed, and subtitles."""
    logging.info("Assembling final video with FFmpeg (Dynamic Engine).")
    
    audio_duration = get_audio_duration(audio_path)
    veo_duration = 8.0 # Veo video is 8 seconds
    fade_duration = 0.5
    
    # Total time to fill with images
    total_image_time = max(1.0, audio_duration - veo_duration + fade_duration + 0.5)
    num_images = len(image_paths)
    
    # We need to account for the crossfades between images.
    # N images means N-1 crossfades between them.
    # Time per image = (total_image_time + (N-1) * fade_duration) / N
    time_per_image = (total_image_time + (num_images - 1) * fade_duration) / num_images
    
    # Select a random audio track from the library
    audio_library_files = glob.glob(os.path.join("audio_library", "*.mp3")) + glob.glob(os.path.join("audio_library", "*.wav"))
    ambient_path = None
    has_ambient = False
    if audio_library_files:
        ambient_path = random.choice(audio_library_files)
        has_ambient = True
        logging.info(f"Selected ambient track: {ambient_path}")
    
    command = [
        "ffmpeg", "-y",
        "-i", video_path,
    ]
    
    # Add all images as inputs
    for img in image_paths:
        command.extend(["-loop", "1", "-t", str(time_per_image), "-i", img])
        
    command.extend(["-i", audio_path])
    audio_input_idx = len(image_paths) + 1
    
    if has_ambient:
        command.extend(["-stream_loop", "-1", "-i", ambient_path])
        ambient_input_idx = audio_input_idx + 1
        
    # Build filter_complex
    # 1. Scale/format Veo hook
    filter_complex = "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24,format=yuv420p[v0];"
    
    # 2. Scale/format/Ken Burns for all images
    for i in range(num_images):
        input_idx = i + 1
        # Alternate zoom direction for variety (zoom in vs zoom out)
        if i % 2 == 0:
            zoom_str = "z='1.05+0.0005*in'" # Zoom in
        else:
             zoom_str = "z='1.2-0.0005*in'" # Zoom out
             
        filter_complex += (
            f"[{input_idx}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2,"
            f"zoompan={zoom_str}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(time_per_image*24)}:s=1080x1920:fps=24,format=yuv420p[img{i}];"
        )
        
    # 3. Chain the crossfades
    # First crossfade: Veo hook -> Image 0
    current_video_stream = "v0"
    current_time = veo_duration - fade_duration
    
    filter_complex += f"[{current_video_stream}][img0]xfade=transition=fade:duration={fade_duration}:offset={current_time}[fade0];"
    current_video_stream = "fade0"
    current_time += time_per_image - fade_duration
    
    # Subsequent crossfades: Image N -> Image N+1
    for i in range(1, num_images):
        filter_complex += f"[{current_video_stream}][img{i}]xfade=transition=fade:duration={fade_duration}:offset={current_time}[fade{i}];"
        current_video_stream = f"fade{i}"
        current_time += time_per_image - fade_duration
        
    final_video_stream = current_video_stream
    
    # Add subtitles if available
    if subtitle_path and os.path.exists(subtitle_path):
        # Escape path for FFmpeg filter
        safe_sub_path = subtitle_path.replace("\\", "/").replace(":", "\\:")
        filter_complex += f"[{final_video_stream}]subtitles='{safe_sub_path}':force_style='Alignment=2,MarginV=150,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2'[v];"
    else:
        filter_complex += f"[{final_video_stream}]copy[v];"
    
    if has_ambient:
        # Mix TTS audio with the ambient bed, increasing ambient volume slightly
        filter_complex += f"[{audio_input_idx}:a][{ambient_input_idx}:a]amix=inputs=2:duration=first:dropout_transition=2:weights=1 0.4[a];"
        audio_map = "[a]"
    else:
        audio_map = f"[{audio_input_idx}:a]"
        
    command.extend([
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", audio_map,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        "-t", str(audio_duration + 1.0),
        output_path
    ])
    
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f"Final video successfully assembled and saved to {output_path}.")
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg assembly failed: {e.stderr.decode()}")
        sys.exit(1)

def main():
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        logging.error("GOOGLE_CLOUD_PROJECT environment variable is missing.")
        sys.exit(1)

    os.makedirs("output", exist_ok=True)
    
    client = genai.Client(vertexai=True, project=project_id, location="us-central1")
    
    content_data = generate_script_and_prompts(client)
    
    veo_video_path = os.path.join("output", "veo_hook.mp4")
    audio_path = os.path.join("output", "narration.wav")
    final_output_path = os.path.join("output", f"final_video_{int(time.time())}.mp4")

    generate_veo_video(client, content_data["veo_prompt"], veo_video_path)
    
    image_paths = []
    for i, img_prompt in enumerate(content_data.get("image_prompts", [])):
        img_path = os.path.join("output", f"nano_banana_fill_{i}.jpg")
        try:
            generate_nano_banana_image(client, img_prompt, img_path)
            if os.path.exists(img_path):
                image_paths.append(img_path)
        except SystemExit:
            logging.error(f"Failed to generate image {i}, skipping to next.")
        # Sleep to avoid hitting the strict Requests Per Minute (RPM) quota on Imagen 3
        time.sleep(25)
            
    # Fallback in case generation fails entirely
    if not image_paths and "image_prompt" in content_data:
        fallback_path = os.path.join("output", "nano_banana_fill.jpg")
        try:
            generate_nano_banana_image(client, content_data["image_prompt"], fallback_path)
            if os.path.exists(fallback_path):
                image_paths.append(fallback_path)
        except SystemExit:
             logging.error("Fallback image generation also failed.")

    generate_gcp_audio(content_data["narration"], audio_path)
    
    subtitle_path = ""
    if os.path.exists(audio_path):
        subtitle_path = generate_subtitles(audio_path, "output")
    
    if image_paths and os.path.exists(veo_video_path):
        assemble_video(veo_video_path, image_paths, audio_path, final_output_path, subtitle_path)
        
        logging.info("Initiating YouTube upload sequence.")
        youtube = get_authenticated_service()
        upload_video(
            youtube=youtube,
            file_path=final_output_path,
            title=content_data["title"],
            description=content_data["description"]
        )
        
        logging.info("Initiating Meta upload sequence.")
        upload_to_meta(
            file_path=final_output_path,
            title=content_data["title"],
            description=content_data["description"],
            platform="facebook"
        )
        
        logging.info("Logging content to SQLite ledger.")
        log_content(title=content_data["title"], fact_summary=content_data["narration"])
        
        logging.info("Cleaning up temporary local files...")
        # Keep the final mp4 around for a day just in case, but clean up the heavy intermediate files
        for temp_file in [veo_video_path, audio_path, subtitle_path] + image_paths:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    logging.warning(f"Failed to delete {temp_file}: {e}")
                    
        # Delete final outputs older than 2 days
        import time as time_module
        now = time_module.time()
        for f in os.listdir("output"):
            f_path = os.path.join("output", f)
            if f.endswith(".mp4") and os.path.isfile(f_path):
                if os.stat(f_path).st_mtime < now - (2 * 86400):
                    try:
                        os.remove(f_path)
                    except:
                        pass
        logging.info("Cleanup complete.")
        
    else:
        logging.warning("Media assets not found at target paths. Skipping assembly and upload.")

if __name__ == "__main__":
    main()
