import asyncio
import edge_tts
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, TextClip, CompositeVideoClip, VideoFileClip, CompositeAudioClip, concatenate_audioclips
from moviepy.video.fx.Resize import Resize
from moviepy.video.fx import CrossFadeIn, CrossFadeOut, FadeIn, FadeOut, SlideIn, SlideOut
from moviepy import AudioFileClip, afx
import os
import whisper
import logging
from datetime import date, datetime
import warnings
from utils import setup_logger
import config
import random

# Filtrar warnings de tipo UserWarning
warnings.filterwarnings("ignore", category=UserWarning)

class VideoGenerator:
    def __init__(self, project_manager, music_style='horror'):
        self.project_manager = project_manager
        self.logger = setup_logger(__name__)
        self.VIDEO_SIZE = config.VIDEO_SIZE
        self.FONT_SIZE = config.FONT_SIZE
        self.music_style = music_style

    async def generar_audio(self, texto, capitulo_num):
        """Genera un archivo de audio a partir de texto"""
        output_file = os.path.join(
            self.project_manager.get_path('audio'),
            f"chapter_{capitulo_num}_audio.mp3"
        )
        try:
            self.logger.info(f"Generating audio for chapter {capitulo_num}")
            communicate = edge_tts.Communicate(texto, config.TTS_VOICE)
            await communicate.save(output_file)
            return output_file
        except Exception as e:
            self.logger.error(f"Error generating audio: {e}")
            return None

    async def esperar_archivo(self, file_path, timeout=60, stable_checks=5, check_interval=0.5):
        """Espera hasta que un archivo exista, tenga tamaño > 0 y su tamaño permanezca estable."""
        elapsed = 0
        stable_count = 0
        last_size = -1

        logging.info(f"Esperando archivo '{file_path}' (timeout={timeout}s, stable_checks={stable_checks}, check_interval={check_interval}s)")
        while elapsed < timeout:
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                current_size = os.path.getsize(file_path)
                logging.debug(f"Archivo '{file_path}' existe, tamaño actual: {current_size} bytes (anterior: {last_size} bytes), stable_count={stable_count}")
                if current_size == last_size:
                    stable_count += 1
                    logging.debug(f"Tamaño estable por {stable_count}/{stable_checks} chequeos.")
                else:
                    stable_count = 0
                    last_size = current_size
                    logging.debug(f"Tamaño cambió, reiniciando contador de estabilidad.")
                if stable_count >= stable_checks:
                    logging.info(f"Archivo '{file_path}' está listo para usar.")
                    return True
            else:
                if not os.path.exists(file_path):
                    logging.debug(f"Archivo '{file_path}' no existe aún.")
                else:
                    logging.debug(f"Archivo '{file_path}' existe pero tamaño es 0 bytes.")
                stable_count = 0
                last_size = -1
            await asyncio.sleep(check_interval)
            elapsed += check_interval
        logging.warning(f"Timeout alcanzado esperando archivo '{file_path}'.")
        return False

    def transcribir_audio(self, audio_path, capitulo_num):
        """Transcribe un archivo de audio utilizando la librería whisper"""
        output_file = os.path.join(
            self.project_manager.get_path('subtitles'),
            f"chapter_{capitulo_num}_subs.srt"
        )
        transcript_file = os.path.join(
            self.project_manager.get_path('script'),
            f"chapter_{capitulo_num}_transcript.txt"
        )
        try:
            self.logger.info(f"Transcribiendo audio desde '{audio_path}'")
            if not os.path.exists(audio_path):
                logging.error(f"El archivo de audio '{audio_path}' no existe.")
                return None, None
            model = whisper.load_model("small")
            result = model.transcribe(audio_path)
            subtitulos = []
            transcript_text = ""
            for segment in result["segments"]:
                start = segment["start"]
                end = segment["end"]
                text = segment["text"]
                subtitulos.append(((start, end), text))
                transcript_text += text.strip() + " "
            logging.info(f"Transcripción completada. Se encontraron {len(subtitulos)} segmentos. Guardando en '{output_file}' y '{transcript_file}'")
            # Guardar la transcripción completa en un archivo de texto
            with open(transcript_file, "w", encoding="utf-8") as f:
                f.write(transcript_text.strip())
            # Guardar los subtítulos en un archivo .srt
            with open(output_file, "w", encoding="utf-8") as f:
                for idx, ((start, end), text) in enumerate(subtitulos, 1):
                    # Formato SRT: hh:mm:ss,ms
                    def srt_time(t):
                        h = int(t // 3600)
                        m = int((t % 3600) // 60)
                        s = int(t % 60)
                        ms = int((t - int(t)) * 1000)
                        return f"{h:02}:{m:02}:{s:02},{ms:03}"
                    f.write(f"{idx}\n{srt_time(start)} --> {srt_time(end)}\n{text.strip()}\n\n")
            return subtitulos, output_file
        except Exception as e:
            logging.error(f"Error al transcribir el audio '{audio_path}': {e}")
            return None, None

    def crear_clips_de_subtitulos(self, subtitulos):
        """Crea clips de texto para los subtítulos."""
        clips_de_texto = []
        try:
            self.logger.info(f"Creando {len(subtitulos)} clips de subtítulos.")
            
            for (start, end), texto in subtitulos:
                
                texto_clip = (TextClip(
                    text=texto,
                    font=config.FONT_PATH,
                    font_size=config.FONT_SIZE,
                    color=config.SUBTITLE_STYLE['color'],
                    stroke_color=config.SUBTITLE_STYLE['stroke_color'],
                    stroke_width=config.SUBTITLE_STYLE['stroke_width'],
                    margin=config.SUBTITLE_STYLE['margin'],
                    method=config.SUBTITLE_STYLE['method'],
                    size=config.SUBTITLE_STYLE['size'],
                    text_align=config.SUBTITLE_STYLE['text_align'],
                    interline=config.SUBTITLE_STYLE['interline']
                )
                .with_position(config.SUBTITLE_STYLE['position'])
                .with_start(start)
                .with_end(end))
                
                clips_de_texto.append(texto_clip)
            
            self.logger.info(f"Clips de subtítulos creados correctamente.")
            return clips_de_texto
        except Exception as e:
            self.logger.error(f"Error al crear los clips de subtítulos: {e}")
            return []

    def crear_video_con_imagenes_y_subtitulos(self, lista_imagenes, audio_path, subtitulos, capitulo_num):
        """Crea un video combinando imágenes, audio y subtítulos"""
        output_video = os.path.join(
            self.project_manager.get_path('video'),
            f"chapter_{capitulo_num}.mp4"
        )
        audio_clip = None
        try:
            logging.info(f"Creando video '{output_video}' con {len(lista_imagenes)} imágenes y subtítulos.")
            audio_clip = AudioFileClip(audio_path)
            duracion_audio = audio_clip.duration
            num_imagenes = len(lista_imagenes)

            if num_imagenes > 0 and duracion_audio > 0:
                duracion_por_imagen = duracion_audio / num_imagenes
                clips_de_imagen = [
                    ImageClip(img_path, duration=duracion_por_imagen).with_effects([Resize(new_size=self.VIDEO_SIZE)])
                    for img_path in lista_imagenes
                ]
                video_principal = concatenate_videoclips(clips_de_imagen)
                video_principal = CompositeVideoClip([video_principal], size=self.VIDEO_SIZE)
                clips_de_subtitulos = self.crear_clips_de_subtitulos(subtitulos)
                video_final = CompositeVideoClip([video_principal] + clips_de_subtitulos, size=self.VIDEO_SIZE)
                video_final.audio = audio_clip  # Asigna el audio aquí
                video_final.write_videofile(output_video, fps=24, codec='libx264', audio_codec='aac')
                logging.info(f"Video '{output_video}' creado exitosamente.")
                return output_video
            else:
                logging.warning("No se proporcionaron imágenes o la duración del audio es cero. No se generó el video.")
                return None
        except FileNotFoundError:
            logging.error(f"No se encontró el archivo de audio en '{audio_path}'.")
            return None
        except Exception as e:
            logging.error(f"Error al crear el video: {e}")
            return None
        finally:
            if audio_clip:
                audio_clip.close()

    async def create_chapter_videos(self, story_info):
        """Create videos for each chapter"""
        try:
            self.logger.info("Starting chapter videos creation")
            chapter_videos = []
            
            for i, chapter in enumerate(story_info['chapters'], 1):
                self.logger.info(f"Processing chapter {i}...")
                
                # Read Russian text for audio generation
                with open(chapter['text_ru_path'], 'r', encoding='utf-8') as f:
                    chapter_text = f.read()
                
                # Generate audio for this chapter
                audio_path = await self.generar_audio(chapter_text, i)
                if not audio_path:
                    self.logger.error(f"Failed to generate audio for chapter {i}")
                    continue

                # Generate subtitles
                subtitles, _ = self.transcribir_audio(audio_path, i)
                if not subtitles:
                    self.logger.error(f"Failed to generate subtitles for chapter {i}")
                    continue

                # Create video for this chapter
                self.logger.info(f"Creating video for chapter {i}...")
                chapter_video = self.crear_video_con_imagenes_y_subtitulos(
                    [chapter['image_path']],
                    audio_path,
                    subtitles,
                    i
                )
                if chapter_video:
                    chapter_videos.append(chapter_video)
                    self.logger.info(f"Chapter {i} video created successfully")
                else:
                    self.logger.error(f"Failed to create video for chapter {i}")

            if chapter_videos:
                self.logger.info("Combining all chapter videos...")
                return self.combine_chapter_videos(chapter_videos)
            
            return None

        except Exception as e:
            self.logger.error(f"Error in create_chapter_videos: {e}", exc_info=True)
            return None

    def apply_random_transition(self, clip1, clip2, transition_type=None):
        """Apply a random transition between two video clips"""
        if transition_type is None:
            transition_type = random.choice(list(config.VIDEO_TRANSITIONS.keys()))
        
        transition_config = config.VIDEO_TRANSITIONS[transition_type]
        duration = transition_config['duration']
        
        try:
            if transition_type == 'fade':
                clip1 = CompositeVideoClip([clip1.with_effects([FadeOut(duration)])])
                clip2 = CompositeVideoClip([clip2.with_effects([FadeIn(duration)])])
                return clip1, clip2
                
            elif transition_type == 'fade_out_fade_in':
                clip1 = CompositeVideoClip([clip1.with_effects([FadeOut(duration / 2)])])
                clip2 = CompositeVideoClip([clip2.with_effects([FadeIn(duration / 2)])])
                return clip1, clip2
                
            elif transition_type == 'crossfade':
                clip1 = CompositeVideoClip([clip1.with_effects([CrossFadeOut(duration)])])
                clip2 = CompositeVideoClip([clip2.with_effects([CrossFadeIn(duration)])])
                return clip1, clip2
                
            elif transition_type == 'slide':
                direction = transition_config.get('direction', 'left')
                clip1 = CompositeVideoClip([clip1.with_effects([SlideOut(duration, direction)])])
                clip2 = CompositeVideoClip([clip2.with_effects([SlideIn(duration, direction)])])
                return clip1, clip2
                
            elif transition_type == 'wipe':
                direction = transition_config.get('direction', 'right')
                clip1 = CompositeVideoClip([clip1.with_effects([SlideOut(duration, direction)])])
                clip2 = CompositeVideoClip([clip2.with_effects([SlideIn(duration, direction)])])
                return clip1, clip2
                
        except Exception as e:
            self.logger.warning(f"Error applying transition {transition_type}, falling back to cut: {e}")
            return clip1, clip2

    def get_random_music_track(self):
        """Selecciona una pista de música aleatoria del estilo especificado"""
        try:
            style_dir = os.path.join('music', self.music_style)
            if not os.path.exists(style_dir):
                self.logger.error(f"Music style directory not found: {style_dir}")
                return None
                
            music_files = [f for f in os.listdir(style_dir) 
                          if f.endswith(('.mp3', '.wav'))]
            
            if not music_files:
                self.logger.error(f"No music files found in {style_dir}")
                return None
                
            return os.path.join(style_dir, random.choice(music_files))
        except Exception as e:
            self.logger.error(f"Error selecting music track: {e}")
            return None

    def create_background_music(self, video_duration):
        """Crea una pista de música de fondo que coincida con la duración del video"""
        try:
            music_path = self.get_random_music_track()
            if not music_path:
                return None

            self.logger.info(f"Creating background music from: {music_path}")
            original_music = AudioFileClip(music_path)
            style_config = config.MUSIC_CONFIG['styles'][self.music_style]

            # Si necesitamos hacer loop
            if original_music.duration < video_duration:
                loops_needed = int(video_duration / original_music.duration) + 1
                self.logger.info(f"Music loop needed: {loops_needed} repetitions")
                
                music_clips = []
                total_duration = 0
                
                while total_duration < video_duration:
                    clip = original_music.copy()
                    clip = clip.with_start(total_duration)
                    
                    remaining_duration = video_duration - total_duration
                    if clip.duration > remaining_duration:
                        clip.duration = remaining_duration
                        clip.end = clip.start + remaining_duration
                    
                    # Aplicar volumen configurado
                    clip = clip.with_effects([afx.MultiplyVolume(style_config['volume'])])
                    music_clips.append(clip)
                    total_duration += clip.duration

                final_music = CompositeAudioClip(music_clips)
            else:
                # Si la música es más larga que el video
                final_music = original_music.copy()
                final_music.duration = video_duration
                final_music.end = video_duration
                final_music = final_music.with_effects([afx.MultiplyVolume(style_config['volume'])])

            original_music.close()
            return final_music
            
        except Exception as e:
            self.logger.error(f"Error creating background music: {e}")
            if 'original_music' in locals():
                original_music.close()
            return None

    def combine_chapter_videos(self, video_paths):
        """
        Combine multiple video files into one with transitions and background music.

        Args:
            video_paths (list): List of paths to chapter video files.

        Returns:
            str: Path to the final combined video file if successful.
            None: If the process fails.
        """
        video_clips = []
        final_clips = []
        final_video = None
        
        try:
            output_video = os.path.join(
                self.project_manager.get_path('video'),
                "final_video.mp4"
            )
            
            self.logger.info("Loading video clips...")
            # Cargar todos los clips de video
            for path in video_paths:
                clip = VideoFileClip(path)
                video_clips.append(clip)
            
            # Aplicar transiciones
            self.logger.info("Applying transitions between chapters...")
            final_clips.append(video_clips[0])
            
            for i in range(1, len(video_clips)):
                prev_clip, current_clip = self.apply_random_transition(
                    final_clips[-1],
                    video_clips[i]
                )
                final_clips[-1] = prev_clip
                final_clips.append(current_clip)
            
            # Combinar clips con transiciones
            self.logger.info("Concatenating clips with transitions...")
            final_video = concatenate_videoclips(final_clips, method="compose")
            
            # Añadir música de fondo
            background_music = self.create_background_music(final_video.duration)
            if background_music:
                self.logger.info("Adding background music...")
                audio_clips = []
                
                if final_video.audio is not None:
                    audio_clips.append(final_video.audio)
                
                audio_clips.append(background_music)
                final_audio = CompositeAudioClip(audio_clips)
                final_video.audio = final_audio

            # Guardar video final
            self.logger.info("Writing final video...")
            final_video.write_videofile(
                output_video, 
                fps=config.VIDEO_FPS,
                codec=config.VIDEO_CODECS['video'],
                audio_codec=config.VIDEO_CODECS['audio']
            )
            
            return output_video
            
        except Exception as e:
            self.logger.error(f"Error combining videos: {e}")
            return None
            
        finally:
            # Cleanup resources
            try:
                for clip in video_clips:
                    if clip: clip.close()
                for clip in final_clips:
                    if clip: clip.close()
                if final_video: final_video.close()
                if 'background_music' in locals() and background_music:
                    background_music.close()
            except Exception as e:
                self.logger.warning(f"Error during cleanup: {e}")