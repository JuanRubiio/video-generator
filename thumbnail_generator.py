from pollinations import PollinationsAPI
import os
import requests
from utils import setup_logger
from config import VIDEO_SIZE, THUMBNAIL_SYSTEM_PROMPT

class ThumbnailGenerator:
    def __init__(self, project_manager):
        self.logger = setup_logger(__name__)
        self.project_manager = project_manager
        self.pollinations = PollinationsAPI(project_manager)
        self.thumbnail_size = VIDEO_SIZE  # Thumbnail size (width, height)

    async def generate_thumbnail(self, story_info):
        """Generate thumbnail based on story content"""
        try:
            self.logger.info("\nGenerating thumbnail for video...")
            # Read first chapter for context
            with open(story_info['chapters'][0]['text_en_path'], 'r', encoding='utf-8') as f:
                first_chapter = f.read()

            self.logger.info("Creating thumbnail prompt from first chapter...")
            # Generate an impactful thumbnail prompt
            thumbnail_prompt = await self.pollinations.synthesize_text(
                first_chapter,
                system_prompt=THUMBNAIL_SYSTEM_PROMPT
            )

            self.logger.info("Generating thumbnail image...")
            # Generate the thumbnail image
            thumb_path = os.path.join(
                self.project_manager.get_path('thumbnail'),
                'thumbnail.png'
            )

            # Generate high-impact image
            image_url = await self.pollinations.generate_image(
                prompt=f"YouTube thumbnail: {thumbnail_prompt}, dramatic lighting, cinematic, high contrast",
                width=self.thumbnail_size[0],
                height=self.thumbnail_size[1],
                model="flux"
            )

            # Save thumbnail
            if image_url:
                self.logger.info(f"Saving thumbnail to: {thumb_path}")
                response = requests.get(image_url, stream=True)
                response.raise_for_status()
                
                with open(thumb_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                self.logger.info("Thumbnail generated successfully!")
                return thumb_path
            return None
        except Exception as e:
            self.logger.error(f"Error generating thumbnail: {e}")
            return None
