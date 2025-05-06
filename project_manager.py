import os
from datetime import datetime
import json
import asyncio
from utils import setup_logger
from config import PROJECT_BASE_DIR, PROJECT_DIRS, LANG_MODEL

class ProjectManager:
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.base_dir = PROJECT_BASE_DIR
        self.current_project = None
        self.project_structure = PROJECT_DIRS

    def create_project(self, prompt):
        """Create a new project directory with timestamp"""
        self.logger.info("\nCreating new project directory...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_name = f"project_{timestamp}"
        project_dir = os.path.join(self.base_dir, project_name)
        
        # Crear estructura de directorios
        for dir_name in self.project_structure.values():
            os.makedirs(os.path.join(project_dir, dir_name), exist_ok=True)

        # Guardar información del proyecto
        project_info = {
            'prompt': prompt,
            'creation_date': datetime.now().isoformat(),
        }

        with open(os.path.join(project_dir, 'project_info.json'), 'w', encoding='utf-8') as f:
            json.dump(project_info, f, indent=2)

        self.current_project = project_dir
        self.logger.info(f"Project created at: {project_dir}")
        return project_dir

    async def generate_youtube_metadata(self, pollinations_api, story_info):
        """Generate SEO-friendly metadata for YouTube based on story content"""
        try:
            self.logger.info("Generating YouTube metadata...")
            
            # Read prompt and first chapter
            with open(os.path.join(self.current_project, 'project_info.json'), 'r', encoding='utf-8') as f:
                project_info = json.load(f)

            with open(story_info['chapters'][0]['text_en_path'], 'r', encoding='utf-8') as f:
                first_chapter = f.read()

            async def generate_with_retry(text, prompt, max_retries=3, delay=5):
                """Helper function to generate text with retries"""
                for attempt in range(max_retries):
                    try:
                        result = await pollinations_api.synthesize_text(text, system_prompt=prompt)
                        if result:
                            return result.strip()
                        raise Exception("Empty response received")
                    except Exception as e:
                        self.logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                        if attempt < max_retries - 1:
                            self.logger.info(f"Waiting {delay} seconds before retry...")
                            await asyncio.sleep(delay)
                        else:
                            self.logger.error(f"All attempts failed for prompt: {prompt[:100]}...")
                            return None

            # Generate title with retries
            self.logger.info("Generating title...")
            title = await generate_with_retry(
                first_chapter,
                "Create a compelling, SEO-friendly YouTube title. Max 60 characters. Make it intriguing but not clickbait."
            )
            if not title:
                return None

            # Add delay between API calls
            await asyncio.sleep(2)

            # Generate description with retries
            self.logger.info("Generating description...")
            description = await generate_with_retry(
                first_chapter,
                f"Create a YouTube description for this horror story. Include: hook, synopsis, and call to action. Max 2000 chars."
            )
            if not description:
                return None

            await asyncio.sleep(2)

            # Generate tags with retries
            self.logger.info("Generating tags...")
            tags_text = await generate_with_retry(
                first_chapter,
                "Generate 10-15 relevant YouTube tags separated by commas. Include genre and theme-specific terms."
            )
            if not tags_text:
                return None

            await asyncio.sleep(2)

            # Generate category with retries
            self.logger.info("Determining category...")
            category = await generate_with_retry(
                first_chapter,
                "What is the most appropriate YouTube category? Choose ONE from: Film & Animation, Entertainment, Education, People & Blogs"
            )
            if not category:
                return None

            # Process and save metadata
            project_info['youtube_metadata'] = {
                'title': title,
                'description': description,
                'tags': [tag.strip() for tag in tags_text.split(',') if tag.strip()],
                'category': category,
                'language': {
                    'audio': LANG_MODEL,
                    'subtitles': [LANG_MODEL]
                },
                'visibility': 'Public',
                'made_for_kids': False,
                'custom_thumbnail': 'thumbnail.png'
            }

            # Save updated project info
            with open(os.path.join(self.current_project, 'project_info.json'), 'w', encoding='utf-8') as f:
                json.dump(project_info, f, indent=2, ensure_ascii=False)

            self.logger.info("YouTube metadata generated and saved successfully")
            return project_info['youtube_metadata']

        except Exception as e:
            self.logger.error(f"Error generating YouTube metadata: {e}")
            return None

    def get_path(self, category):
        """Get path for a specific category in current project"""
        if not self.current_project or category not in self.project_structure:
            self.logger.error(f"Invalid project or category: {category}")
            raise ValueError("Invalid project or category")
        return os.path.join(self.current_project, self.project_structure[category])
