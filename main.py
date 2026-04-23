import os
import requests
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip
from dotenv import load_dotenv

load_dotenv()

class NewstogramReels:
    def __init__(self):
        self.news_api_key = os.getenv("94c311a0bd5a43e3a136ef1e7f863213")
        self.width = 1080
        self.height = 1920  # Vertical 9:16 ratio for Reels
        self.bg_color = (20, 20, 20)  # Dark theme
        self.text_color = (255, 255, 255)

    def fetch_latest_news(self):
        """Fetches the top headline."""
        url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={self.news_api_key}"
        response = requests.get(url).json()
        if response["status"] == "ok" and response["articles"]:
            article = response["articles"][0]
            return article["title"], article["description"]
        return "No News Found", "Could not fetch the latest updates."

    def create_news_frame(self, title, description):
        """Creates a high-quality vertical image frame."""
        img = Image.new('RGB', (self.width, self.height), color=self.bg_color)
        draw = ImageDraw.Draw(img)
        
        # Simple text placement (Improve this with text-wrapping logic)
        font_title = ImageFont.load_default() 
        draw.text((100, 400), f"BREAKING NEWS:\n{title}", fill=self.text_color, font=font_title)
        draw.text((100, 800), description[:200] + "...", fill=(200, 200, 200), font=font_title)
        
        frame_path = "temp_frame.png"
        img.save(frame_path)
        return frame_path

    def generate_audio(self, text):
        """Converts text to speech."""
        tts = gTTS(text=text, lang='en')
        audio_path = "temp_audio.mp3"
        tts.save(audio_path)
        return audio_path

    def assemble_reel(self, image_path, audio_path, output_name="news_reel.mp4"):
        """Stitches the image and audio into a video file."""
        audio_clip = AudioFileClip(audio_path)
        
        # Create a video clip that lasts as long as the audio
        video_clip = ImageClip(image_path).set_duration(audio_clip.duration)
        video_clip = video_clip.set_audio(audio_clip)
        
        # Optional: Add a subtle 'zoom' effect for engagement
        video_clip = video_clip.resize(lambda t: 1 + 0.02 * t)  # Slow 2% zoom
        
        video_clip.write_videofile(output_name, fps=24, codec="libx264")
        
        # Cleanup temporary files
        os.remove(image_path)
        os.remove(audio_path)

    def run(self):
        print("--- Starting News-to-Reel Pipeline ---")
        title, desc = self.fetch_latest_news()
        print(f"Processing: {title}")
        
        img_path = self.create_news_frame(title, desc)
        aud_path = self.generate_audio(f"{title}. {desc}")
        
        self.assemble_reel(img_path, aud_path)
        print("--- Reel Generated Successfully! ---")

if __name__ == "__main__":
    bot = NewstogramReels()
    bot.run()