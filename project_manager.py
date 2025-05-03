import os
from datetime import datetime
import json
from utils import setup_logger
from config import PROJECT_BASE_DIR, PROJECT_DIRS

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
            'timestamp': timestamp,
            'prompt': prompt,
            'creation_date': datetime.now().isoformat(),
            'status': 'initialized'
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
            original_prompt = project_info['prompt']

            with open(story_info['chapters'][0]['text_en_path'], 'r', encoding='utf-8') as f:
                first_chapter = f.read()

            # Generate title based on content
            title_prompt = """Analyze the story and create a YouTube title that:
            1. Captures the main theme and genre
            2. Is engaging and SEO-friendly
            3. Maximum 60 characters
            4. Includes main keywords naturally
            Base it ONLY on the actual content, not assumptions."""
            
            title = await pollinations_api.synthesize_text(first_chapter, system_prompt=title_prompt)

            # Generate description based on actual content
            description_prompt = f"""Based on this story content and original prompt: '{original_prompt}',
            create a YouTube description that:
            1. First paragraph: Hook viewers with the core premise
            2. Second paragraph: Brief, engaging synopsis
            3. Final paragraph: Call to action
            4. Include relevant genre-specific keywords naturally
            5. Maximum 2000 characters
            Focus only on the actual content."""
            
            description = await pollinations_api.synthesize_text(first_chapter, system_prompt=description_prompt)

            # Generate tags based on content
            tags_prompt = f"""Based on this story content and original prompt: '{original_prompt}',
            generate YouTube tags that:
            1. Include story-specific keywords
            2. Mix of short and long-tail keywords
            3. Include genre and theme-specific terms
            4. 15-20 tags total
            Use ONLY tags relevant to the actual content."""
            
            tags_text = await pollinations_api.synthesize_text(first_chapter, system_prompt=tags_prompt)
            tags = [tag.strip() for tag in tags_text.split(',')]

            # Detect category and themes from content
            category_prompt = "Analyze this content and determine the most appropriate YouTube category. Choose from: Film & Animation, Entertainment, Education, or People & Blogs."
            category = await pollinations_api.synthesize_text(first_chapter, system_prompt=category_prompt)

            # Generate playlist suggestions based on content
            playlist_prompt = "Based on this story's themes and genre, suggest 3 relevant YouTube playlist names."
            playlists = (await pollinations_api.synthesize_text(first_chapter, system_prompt=playlist_prompt)).split(',')

            project_info['youtube_metadata'] = {
                'title': title.strip(),
                'description': description.strip(),
                'tags': tags,
                'category': category.strip(),
                'language': {
                    'audio': 'ru',
                    'subtitles': ['en']
                },
                'visibility': 'Public',
                'made_for_kids': False,
                'playlist_suggestions': [p.strip() for p in playlists],
                'custom_thumbnail': 'thumbnail.png',
                'engagement_signals': {
                    'cards_timestamp': [],
                    'end_screen': True,
                    'chapters': []
                }
            }

            # Guardar información actualizada
            with open(os.path.join(self.current_project, 'project_info.json'), 'w', encoding='utf-8') as f:
                json.dump(project_info, f, indent=2)

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
