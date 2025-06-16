# Video settings
VIDEO_SIZE = (1920, 1080)  # Standard YouTube HD
VIDEO_FPS = 24
VIDEO_CODECS = {
    'video': 'libx264',
    'audio': 'aac'
}

# Text and fonts
FONT_SIZE = 50
FONT_PATH = "fonts\\DejaVuSans.ttf"  # Font that supports Cyrillic

# Subtitle styling
SUBTITLE_STYLE = {
    'color': '#FFE433',  # Amarillo brillante
    'method': 'caption',
    'stroke_color': 'black',
    'stroke_width': 2,
    'position': ('center', 'bottom'), 
    'margin': (0, 0, 0, 60),  # Margen vertical entre los subtítulos y la parte inferior
    'size': (1000, None),  # Ancho máximo para los subtítulos (ajustar según necesidad)
    'text_align': 'center',  # Alineación del texto
    'interline': -1,  # Espaciado entre líneas ligeramente reducido
    'max_chars': 50  # Máximo de caracteres por línea
}

# Audio settings
TTS_VOICE = "ru-RU-DmitryNeural"
WHISPER_MODEL = "small"
LANG_MODEL = "ru"

# File paths and structure
PROJECT_BASE_DIR = "projects"
SYSTEM_PROMPTS_DIR = "system_prompts"
DEFAULT_SYSTEM_PROMPT = "russian_horror.txt"
LOGS_DIR = "logs"

# Project structure
PROJECT_DIRS = {
    'script': 'script',      # Russian and English texts
    'images': 'images',      # Chapter images
    'audio': 'audio',       # Voice files
    'subtitles': 'subs',    # Subtitles
    'video': 'video',       # Chapter videos and final
    'thumbnail': 'thumb',   # YouTube thumbnail
    'temp': 'temp'          # Temporary files
}

# API settings
POLLINATIONS_CONFIG = {
    'referrer': "VideoGenerator",
    'image_base_url': "https://image.pollinations.ai",
    'text_base_url': "https://text.pollinations.ai",
    'default_model': "turbo",
    'default_text_model': "openai"
}

THUMBNAIL_SYSTEM_PROMPT = "Create a single, impactful scene description for a YouTube thumbnail. Focus on the most dramatic or attention-grabbing elements. Maximum 50 words."


IMAGE_WIDTH = 2560  # Width for generated images
IMAGE_HEIGHT = 1440  # Height for generated images

# Retry settings
RETRY_CONFIG = {
    'max_retries': 3,
    'delay': 5
}

# Video transitions
VIDEO_TRANSITIONS = {
    'fade': {
        'duration': 1.0,
        'color': 'black'
    },
    'fade_out_fade_in': {
        'duration': 1.5,
        'color': 'black'
    },
    'crossfade': {
        'duration': 1.0
    },
    'slide': {
        'duration': 1.0,
        'direction': 'left'  # left, right, up, down
    },
    'wipe': {
        'duration': 1.0,
        'direction': 'right'
    }
}

# Music settings
MUSIC_CONFIG = {
    'base_dir': 'music',
    'styles': {
        'horror': {
            'volume': 0.3,  # 30% del volumen original
            'fade_duration': 2.0  # segundos para fade in/out
        },
        'suspense': {
            'volume': 0.25,
            'fade_duration': 2.0
        },
        'ambient': {
            'volume': 0.2,
            'fade_duration': 1.5
        },
        'dark': {
            'volume': 0.35,
            'fade_duration': 2.0
        }
    },
    'default_style': 'horror'
}

