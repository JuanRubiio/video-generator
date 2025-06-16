import requests
import json
import os
from datetime import datetime
import urllib
import argparse
from utils import setup_logger, retry_on_429
import aiohttp
import asyncio  # Añadir esta importación
from config import IMAGE_HEIGHT, IMAGE_WIDTH, POLLINATIONS_CONFIG

class PollinationsAPI:
    def __init__(self, project_manager):
        self.logger = setup_logger(__name__)
        self.base_url_image = POLLINATIONS_CONFIG['image_base_url']
        self.base_url_text = POLLINATIONS_CONFIG['text_base_url']
        self.project_manager = project_manager
        self.referrer = "VideoGenerator"  # Añadido el referrer faltante
        
        
    def load_system_prompt(self, prompt_file):
        """Load system prompt from a file"""
        try:
            file_path = os.path.join("system_prompts", prompt_file)
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            self.logger.error(f"Error loading system prompt: {e}")
            return None

    @retry_on_429()
    async def generate_image(self, prompt, model="flux", width=IMAGE_WIDTH, height=IMAGE_HEIGHT, seed=None, nologo=True, private=False):
        """Generate an image using the Pollinations API"""
        self.logger.info(f"Generating image with prompt: {prompt}")
        params = {
            'prompt': prompt,
            'model': model,
            'width': width,
            'height': height,
            'nologo': str(nologo).lower(),
            'private': str(private).lower(),
            'enhance': 'true'
        }
        if seed is not None:
            params['seed'] = seed
        if self.referrer:
            params['referrer'] = self.referrer
            
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url_image}/prompt/{prompt}", params=params) as response:
                if response.status == 200:
                    return str(response.url)
        return None

    @retry_on_429()
    async def generate_text(self, prompt, model="openai", system_prompt_file=None, seed=None):
        """Generate text using the Pollinations API"""
        self.logger.info(f"Generating text with prompt: {prompt}")
        try:
            # Load system prompt from file if provided
            system_prompt = None
            if system_prompt_file:
                system_prompt = self.load_system_prompt(system_prompt_file)

            # URL encode the prompt and system prompt
            encoded_prompt = urllib.parse.quote(prompt)
            encoded_system = urllib.parse.quote(system_prompt) if system_prompt else None

            # Build parameters
            params = {}
            if model:
                params['model'] = model
            if seed:
                params['seed'] = seed
            if encoded_system:
                params['system'] = encoded_system

            # Make the request with the correct URL format
            url = f"{self.base_url_text}/{encoded_prompt}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    return await response.text()
        except aiohttp.ClientError as e:
            print(f"Error generating text: {e}")
            return None

    async def generate_and_save_image_to_path(self, prompt, save_path):
        """Generate image and save to specific path"""
        try:
            self.logger.info(f"Generating image with prompt: {prompt}")
            params = {
                'prompt': prompt,
                'model': POLLINATIONS_CONFIG['default_model'],
                'width': IMAGE_WIDTH,
                'height': IMAGE_HEIGHT,
                'nologo': 'true',
                'private': 'false',
                'referrer': self.referrer,
                'seed': int.from_bytes(os.urandom(4), 'big'),
                'enhance': 'true'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url_image}/prompt/{prompt}", params=params) as response:
                    if response.status == 200:
                        image_url = str(response.url)
                        async with session.get(image_url) as img_response:
                            img_response.raise_for_status()
                            with open(save_path, 'wb') as f:
                                while True:
                                    chunk = await img_response.content.read(8192)
                                    if not chunk:
                                        break
                                    f.write(chunk)
                            return save_path
            return None
        except Exception as e:
            self.logger.error(f"Error saving image: {e}")
            return None

    async def generate_chapter_image(self, chapter_text):
        """Generate an image based on the chapter's main scene"""
        scene_description = await self.synthesize_chapter(chapter_text)
        if not scene_description:
            return None

        self.logger.info(f"Generating image for scene: {scene_description}")
        return await self.generate_and_save_image_to_path(
            f"cinematic scene: {scene_description}. Dramatic lighting, high contrast, cinematic style",
            os.path.join(
                self.project_manager.get_path('images'),
                f"chapter_{len(os.listdir(self.project_manager.get_path('images'))) + 1}.png"
            )
        )

    async def generate_and_save_text(self, prompt, model=None, system_prompt_file=None, seed=None):
        """Generate text and save it with chapters and images"""
        try:
            text = await self.generate_text(prompt, model, system_prompt_file, seed)
            if not text:
                self.logger.error("Failed to generate initial text")
                return None

            complete_story_path = os.path.join(
                self.project_manager.get_path('script'), 
                "complete_story_ru.txt"
            )
            with open(complete_story_path, "w", encoding="utf-8") as f:
                f.write(text)
            
            chapters = self.extract_chapters(text)
            chapter_info = []
            
            for i, chapter in enumerate(chapters, 1):
                self.logger.info(f"\nProcessing chapter {i}...")
                try:
                    # Save Russian version
                    chapter_ru_path = os.path.join(
                        self.project_manager.get_path('script'),
                        f"chapter_{i}_ru.txt"
                    )
                    with open(chapter_ru_path, "w", encoding="utf-8") as f:
                        f.write(chapter)
                    
                    # Process chapter with retries
                    max_retries = 3
                    chapter_processed = False
                    
                    for attempt in range(max_retries):
                        try:
                            self.logger.info(f"Processing chapter {i} attempt {attempt + 1}/{max_retries}")
                            
                            # Translation
                            chapter_en = await self.translate_text(chapter)
                            if not chapter_en:
                                raise Exception(f"Translation failed for chapter {i}")
                            
                            chapter_en_path = os.path.join(
                                self.project_manager.get_path('script'),
                                f"chapter_{i}_en.txt"
                            )
                            with open(chapter_en_path, "w", encoding="utf-8") as f:
                                f.write(chapter_en)
                            
                            # Image generation
                            image_path = await self.generate_chapter_image(chapter_en)
                            if not image_path:
                                raise Exception(f"Image generation failed for chapter {i}")
                            
                            chapter_info.append({
                                'text_ru_path': chapter_ru_path,
                                'text_en_path': chapter_en_path,
                                'image_path': image_path
                            })
                            
                            chapter_processed = True
                            break
                            
                        except Exception as e:
                            self.logger.error(f"Attempt {attempt + 1} failed for chapter {i}: {e}")
                            if attempt < max_retries - 1:
                                self.logger.info(f"Waiting 5 seconds before retry...")
                                await asyncio.sleep(5)
                            else:
                                self.logger.error(f"Failed to process chapter {i} after {max_retries} attempts")
                                return None
                    
                    if not chapter_processed:
                        self.logger.error(f"Failed to process chapter {i}")
                        return None
                        
                except Exception as e:
                    self.logger.error(f"Unexpected error processing chapter {i}: {e}")
                    return None
            
            # Save chapter information
            info_path = os.path.join(self.project_manager.current_project, "story_info.json")
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump({
                    'complete_story_ru': complete_story_path,
                    'chapters': chapter_info
                }, f, indent=2)
            
            return self.project_manager.current_project
            
        except Exception as e:
            self.logger.error(f"Error in generate_and_save_text: {e}")
            return None

    def extract_chapters(self, text):
        """Extract chapters from the generated text"""
        chapters = []
        current_chapter = []
        
        for line in text.split('\n'):
            if line.startswith('Глава'):
                if current_chapter:
                    chapters.append('\n'.join(current_chapter))
                current_chapter = [line]
            else:
                current_chapter.append(line)
                
        if current_chapter:
            chapters.append('\n'.join(current_chapter))
            
        return chapters

    @retry_on_429()
    async def translate_text(self, text, model="openai"):
        """Translate text from Russian to English using the API"""
        self.logger.info("Translating text from Russian to English")
        try:
            system_prompt = "You are a professional translator. Translate the following Russian text to English, maintaining the same structure and paragraphs. Translate ONLY the content, do not add any comments or explanations."
            
            encoded_prompt = urllib.parse.quote(text)
            encoded_system = urllib.parse.quote(system_prompt)

            params = {
                'model': model,
                'system': encoded_system
            }

            url = f"{self.base_url_text}/{encoded_prompt}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    return await response.text()
        except aiohttp.ClientError as e:
            print(f"Error translating text: {e}")
            return None

    @retry_on_429()
    async def synthesize_chapter(self, chapter_text, model="openai"):
        """Generate a concise visual description of the chapter's main scene"""
        self.logger.info("Synthesizing chapter description")
        try:
            system_prompt = "You are a visual scene director. Given this chapter of a story, create a single sentence (max 50 words) describing the most impactful or atmospheric scene that would best represent this chapter visually. Focus on mood, setting, and key visual elements. Do not explain, just describe the scene."
            
            encoded_prompt = urllib.parse.quote(chapter_text)
            encoded_system = urllib.parse.quote(system_prompt)

            params = {
                'model': model,
                'system': encoded_system
            }

            url = f"{self.base_url_text}/{encoded_prompt}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    return (await response.text()).strip()
        except aiohttp.ClientError as e:
            print(f"Error synthesizing chapter: {e}")
            return None

    @retry_on_429()
    async def synthesize_text(self, text, system_prompt=None, model="openai"):
        """Generate a concise description or summary of the given text"""
        self.logger.info("Synthesizing text description")
        try:
            if not system_prompt:
                system_prompt = "Create a brief, impactful description from the following text. Focus on the most dramatic elements. Keep it concise and engaging."

            encoded_prompt = urllib.parse.quote(text)
            encoded_system = urllib.parse.quote(system_prompt)

            params = {
                'model': model,
                'system': encoded_system
            }

            url = f"{self.base_url_text}/{encoded_prompt}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    return (await response.text()).strip()
        except aiohttp.ClientError as e:
            self.logger.error(f"Error synthesizing text: {e}")
            return None

async def main():
    parser = argparse.ArgumentParser(description='Generate content using Pollinations API')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Image generation parser
    image_parser = subparsers.add_parser('image', help='Generate an image')
    image_parser.add_argument('prompt', help='Text prompt to generate the image')
    image_parser.add_argument('--width', type=int, default=IMAGE_WIDTH, help='Image width (default: 1920)')
    image_parser.add_argument('--height', type=int, default=IMAGE_HEIGHT, help='Image height (default: 1080)')
    image_parser.add_argument('--model', default='flux', help='Model to use (default: flux)')
    image_parser.add_argument('--seed', type=int, help='Seed for reproducible results')
    
    # Text generation parser
    text_parser = subparsers.add_parser('text', help='Generate text')
    text_parser.add_argument('prompt', help='Text prompt to generate the response')
    text_parser.add_argument('--model', default='openai', help='Model to use for text generation')
    text_parser.add_argument('--system-prompt-file', help='File containing the system prompt')
    text_parser.add_argument('--seed', type=int, help='Seed for reproducible results')
    
    args = parser.parse_args()
    api = PollinationsAPI()

    if args.command == 'image':
        print(f"Generating image for prompt: {args.prompt}")
        image_path = await api.generate_and_save_image(
            prompt=args.prompt,
            model=args.model,
            width=args.width,
            height=args.height,
            seed=args.seed
        )
        if image_path:
            print(f"Image saved successfully at: {image_path}")
        else:
            print("Failed to generate image")
            
    elif args.command == 'text':
        print(f"Generating text for prompt: {args.prompt}")
        story_dir = await api.generate_and_save_text(
            prompt=args.prompt,
            model=args.model,
            system_prompt_file=args.system_prompt_file,
            seed=args.seed
        )
        if story_dir:
            print(f"Story generated successfully at: {story_dir}")
            print("Generated content includes:")
            print("- Complete story text")
            print("- Individual chapter files")
            print("- Chapter images")
            print("- Story information JSON file")
        else:
            print("Failed to generate text")
    else:
        parser.print_help()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())




