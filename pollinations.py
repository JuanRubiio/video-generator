import requests
import json
import os
from datetime import datetime
import urllib.request
import argparse

class PollinationsAPI:
    def __init__(self, referrer=None):
        self.base_url_image = "https://image.pollinations.ai"
        self.base_url_text = "https://text.pollinations.ai"
        self.referrer = referrer
        
        # Create necessary directories
        self.images_dir = "images_input"
        self.texts_dir = "text_input"
        self.prompts_dir = "system_prompts"
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.texts_dir, exist_ok=True)
        os.makedirs(self.prompts_dir, exist_ok=True)

    def load_system_prompt(self, prompt_file):
        """Load system prompt from a file"""
        try:
            file_path = os.path.join(self.prompts_dir, prompt_file)
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            print(f"Error loading system prompt: {e}")
            return None

    def generate_image(self, prompt, model="flux", width=1280, height=720, seed=None, nologo=True, private=False):
        """Generate an image using the Pollinations API"""
        params = {
            'prompt': prompt,
            'model': model,
            'width': width,
            'height': height,
            'nologo': str(nologo).lower(),
            'private': str(private).lower()
        }
        if seed is not None:
            params['seed'] = seed
        if self.referrer:
            params['referrer'] = self.referrer
            
        response = requests.get(f"{self.base_url_image}/prompt/{prompt}", params=params)
        return response.url if response.status_code == 200 else None

    def generate_text(self, prompt, model="openai", system_prompt_file=None, seed=None):
        """Generate text using the Pollinations API"""
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
            if self.referrer:
                params['referrer'] = self.referrer

            # Make the request with the correct URL format
            url = f"{self.base_url_text}/{encoded_prompt}"
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Error generating text: {e}")
            return None

    def generate_and_save_image(self, prompt, model="flux", width=1280, height=720, seed=None, nologo=True, private=False):
        """Generate an image and save it to the images directory"""
        try:
            # Get the image URL
            image_url = self.generate_image(prompt, model, width, height, seed, nologo, private)
            if image_url:
                # Get next image number
                existing_images = len([f for f in os.listdir(self.images_dir) if f.startswith("imagen")])
                image_number = existing_images + 1
                image_path = os.path.join(self.images_dir, f"imagen{image_number}.png")
                
                # Download image using requests
                response = requests.get(image_url, stream=True)
                response.raise_for_status()  # Raise an exception for bad status codes
                
                # Save the image
                with open(image_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        
                return image_path
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error downloading image: {e}")
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

    def translate_text(self, text, model="openai"):
        """Translate text from Russian to English using the API"""
        try:
            system_prompt = "You are a professional translator. Translate the following Russian text to English, maintaining the same structure and paragraphs. Translate ONLY the content, do not add any comments or explanations."
            
            encoded_prompt = urllib.parse.quote(text)
            encoded_system = urllib.parse.quote(system_prompt)

            params = {
                'model': model,
                'system': encoded_system
            }

            url = f"{self.base_url_text}/{encoded_prompt}"
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Error translating text: {e}")
            return None

    def extract_scene_description(self, chapter_text):
        """Extract key visual elements from the chapter text"""
        lines = chapter_text.split('\n')
        title = lines[0] if lines else ""
        
        # Get the first few paragraphs for context
        content = ' '.join(lines[1:4]) if len(lines) > 1 else ""
        
        # Now we can use English words since we're working with translated text
        locations = [word for word in content.split() if any(loc in word.lower() for loc in 
                    ['forest', 'house', 'village', 'city', 'church', 'lake', 'river', 'mountain', 'room', 'castle'])]
        
        time_weather = [word for word in content.split() if any(desc in word.lower() for desc in 
                       ['night', 'day', 'morning', 'evening', 'dark', 'cold', 'snow', 'rain', 'fog', 'mist'])]
        
        return {
            'title': title,
            'location': locations[0] if locations else '',
            'time_weather': time_weather[0] if time_weather else '',
            'content': content[:200]  # First 200 characters for context
        }

    def generate_chapter_image(self, chapter_text):
        """Generate an image based on the chapter content"""
        scene = self.extract_scene_description(chapter_text)
        
        # Create a more specific and varied prompt
        prompt_elements = [
            "Atmospheric horror scene",
            f"in {scene['location']}" if scene['location'] else "in a dark Russian setting",
            f"during {scene['time_weather']}" if scene['time_weather'] else "at night",
            f"from the scene: {scene['content']}"
        ]
        
        image_prompt = ", ".join(filter(None, prompt_elements))
        
        # Add artistic style variations
        styles = [
            "in the style of Russian Gothic art",
            "like a dark oil painting",
            "reminiscent of Soviet era horror",
            "inspired by Slavic folk art"
        ]
        
        # Use chapter number to select different style
        style_index = len(self.extract_chapters(chapter_text)) % len(styles)
        image_prompt += f", {styles[style_index]}"
        
        print(f"Generating image with prompt: {image_prompt}")  # Debug info
        return self.generate_and_save_image(image_prompt)

    def generate_and_save_text(self, prompt, model=None, system_prompt_file=None, seed=None):
        """Generate text and save it with chapters and images"""
        text = self.generate_text(prompt, model, system_prompt_file, seed)
        if text:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            story_dir = os.path.join(self.texts_dir, f"story_{timestamp}")
            os.makedirs(story_dir, exist_ok=True)
            
            # Save complete story in Russian
            complete_story_path = os.path.join(story_dir, "complete_story_ru.txt")
            with open(complete_story_path, "w", encoding="utf-8") as f:
                f.write(text)
            
            chapters = self.extract_chapters(text)
            chapter_info = []
            
            for i, chapter in enumerate(chapters, 1):
                # Save Russian version
                chapter_ru_path = os.path.join(story_dir, f"chapter_{i}_ru.txt")
                with open(chapter_ru_path, "w", encoding="utf-8") as f:
                    f.write(chapter)
                
                # Translate and save English version
                print(f"Translating chapter {i}...")
                chapter_en = self.translate_text(chapter)
                chapter_en_path = os.path.join(story_dir, f"chapter_{i}_en.txt")
                with open(chapter_en_path, "w", encoding="utf-8") as f:
                    f.write(chapter_en)
                
                # Generate image using English translation
                print(f"Generating image for chapter {i}...")
                image_path = self.generate_chapter_image(chapter_en)
                
                chapter_info.append({
                    'text_ru_path': chapter_ru_path,
                    'text_en_path': chapter_en_path,
                    'image_path': image_path
                })
            
            # Save chapter information
            info_path = os.path.join(story_dir, "story_info.json")
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump({
                    'complete_story_ru': complete_story_path,
                    'chapters': chapter_info
                }, f, indent=2)
            
            return story_dir
        return None

def main():
    parser = argparse.ArgumentParser(description='Generate content using Pollinations API')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Image generation parser
    image_parser = subparsers.add_parser('image', help='Generate an image')
    image_parser.add_argument('prompt', help='Text prompt to generate the image')
    image_parser.add_argument('--width', type=int, default=1280, help='Image width (default: 1280)')
    image_parser.add_argument('--height', type=int, default=720, help='Image height (default: 720)')
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
        image_path = api.generate_and_save_image(
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
        story_dir = api.generate_and_save_text(
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
    main()




