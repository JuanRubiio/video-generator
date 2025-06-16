import argparse
import asyncio
from pollinations import PollinationsAPI
from video_generator import VideoGenerator
import json
import os
from utils import setup_logger
from project_manager import ProjectManager
from thumbnail_generator import ThumbnailGenerator
from config import MUSIC_CONFIG

class VideoCreationOrchestrator:
    def __init__(self, interactive=False, music_style=None):
        self.project_manager = ProjectManager()
        self.pollinations = PollinationsAPI(self.project_manager)
        self.video_gen = VideoGenerator(self.project_manager)
        self.thumb_gen = ThumbnailGenerator(self.project_manager)
        self.interactive = interactive
        self.music_style = music_style
        self.logger = setup_logger(__name__)

    async def wait_for_confirmation(self, message):
        if not self.interactive:
            return True
        response = input(f"\n{message} (y/n): ")
        return response.lower() in ['y', 'yes', '']

    async def create_story_and_images(self, prompt, system_prompt_file, music_style):
        self.logger.info(f"Starting story generation with prompt: {prompt}")
        print("\nGenerating story and chapters...")
        # Crear nuevo proyecto
        self.project_manager.create_project(prompt, music_style)
        story_dir = await self.pollinations.generate_and_save_text(
            prompt=prompt,
            system_prompt_file=system_prompt_file
        )
        
        if not story_dir:
            print("Failed to generate story")
            return None

        # Load story information
        with open(os.path.join(story_dir, "story_info.json"), "r", encoding="utf-8") as f:
            story_info = json.load(f)

        if not await self.wait_for_confirmation("Story and chapters generated. Continue with video creation?"):
            return None

        return story_info

    async def create_video(self, story_info):
        print("\nCreating chapter videos...")
        result = await self.video_gen.create_chapter_videos(story_info)
        if result:
            # Generate thumbnail
            thumbnail = await self.thumb_gen.generate_thumbnail(story_info)
            if thumbnail:
                print(f"Thumbnail generated at: {thumbnail}")
                
            # Generate YouTube metadata
            print("\nGenerating YouTube metadata...")
            metadata = await self.project_manager.generate_youtube_metadata(self.pollinations, story_info)
            if metadata:
                print("\nYouTube metadata generated:")
                print(f"Title: {metadata['title']}")
                print(f"Tags: {', '.join(metadata['tags'][:5])}...")
                
            print(f"\nVideo creation completed successfully!")
            print(f"Final video saved at: {result}")
            return True
        return False

    async def run(self, prompt, system_prompt_file, music_style):
        self.logger.info("Starting video creation process")
        story_info = await self.create_story_and_images(prompt, system_prompt_file, music_style)
        if not story_info:
            return False

        await self.create_video(story_info)
        return True

def main():
    parser = argparse.ArgumentParser(description='Create a video from a story prompt')
    parser.add_argument('prompt', help='Prompt for story generation')
    parser.add_argument('--system-prompt', default='russian_horror.txt', 
                       help='System prompt file (default: russian_horror.txt)')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Enable interactive mode with confirmations')
    parser.add_argument('--music-style', 
                       choices=list(MUSIC_CONFIG['styles'].keys()),
                       default=MUSIC_CONFIG['default_style'],
                       help='Style of background music')
    
    args = parser.parse_args()
    
    orchestrator = VideoCreationOrchestrator(
        interactive=args.interactive,
        music_style=args.music_style
    )
    asyncio.run(orchestrator.run(args.prompt, args.system_prompt, args.music_style))

if __name__ == "__main__":
    main()
