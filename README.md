# AI-Powered Narrative Video Generator

An automated system that generates and produces complete any gender story videos 

## Features

- Story Generation 
- Any language Translation
- Image Generation for each chapter
- Text-to-Speech 
- Automatic Subtitling
- Chapter-based Video Creation
- YouTube Thumbnail Generation
- Project-based Organization

## System Requirements

- Python 3.11+
- FFmpeg installed and in PATH
- GPU recommended for faster video processing

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd video-generator

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Create required directories
mkdir fonts
```

## Project Structure

```
video-generator/
├── projects/                  # Generated project folders
├── system_prompts/           # Story generation prompts
├── fonts/                    # Font files
├── logs/                     # Application logs
├── config.py                 # Configuration settings
├── main.py                   # Main application
├── video_generator.py        # Video processing
├── pollinations.py           # AI API integration
├── project_manager.py        # Project structure handling
├── thumbnail_generator.py    # Thumbnail creation
└── utils.py                 # Utility functions
```

## Configuration

Key configuration files:
- `config.py`: Video settings, paths, and styling
- `system_prompts/russian_horror.txt`: Story generation prompt

## Usage

Basic usage:
```bash
python main.py "Write a horror story about an abandoned Soviet research facility"
```

With options:
```bash
python main.py -i --system-prompt custom_prompt.txt "Your story prompt here"
```

Options:
- `-i, --interactive`: Enable interactive mode with confirmations
- `--system-prompt`: Specify custom story prompt file

## Project Output Structure

Each generated project includes:
```
project_[timestamp]/
├── script/                   # Russian and English texts
├── images/                   # Chapter images
├── audio/                    # Voice files
├── subs/                    # Subtitles
├── video/                   # Chapter videos and final
├── thumb/                   # YouTube thumbnail
└── project_info.json        # Project metadata
```

## Features in Detail

### Story Generation
- Generates horror stories 
- Structures content into chapters
- Maintains consistent narrative

### Image Generation
- Creates atmospheric images for each chapter
- Generates YouTube thumbnails
- HD quality (1920x1080)

### Audio
- Text-to-Speech 
- Natural voice
- Synchronized with subtitles

### Video
- HD video output (1280x720)
- Chapter-based structure
- Yellow subtitles with black outline
- Professional formatting

## Error Handling

- Automatic retries for API failures
- Comprehensive logging
- Project state preservation
- Error reporting

## Dependencies

Main dependencies:
- edge-tts: Text-to-Speech
- moviepy: Video processing
- whisper: Speech recognition
- aiohttp: Async HTTP requests

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Credits

- OpenAI Whisper for transcription
- Microsoft Edge TTS for voice synthesis
- Pollinations.ai for image generation