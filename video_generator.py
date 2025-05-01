import asyncio
import edge_tts
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, TextClip, CompositeVideoClip
from moviepy.video.fx.Resize import Resize
import os
import whisper
import logging
from datetime import date, datetime
import warnings

# Filtrar warnings de tipo UserWarning
warnings.filterwarnings("ignore", category=UserWarning)

# Configuración de logging para un único archivo por día
log_file = f"video_generation_{date.today().strftime('%Y%m%d')}.log"
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding="utf-8"  # <-- Añadido para soportar caracteres especiales
)

# Definición de los directorios de salida
OUTPUT_AUDIO_DIR = "audio_output"
OUTPUT_SUBTITLES_DIR = "subtitles_output"
OUTPUT_VIDEO_DIR = "video_output"
OUTPUT_TRANSCRIPTS_DIR = "transcripts_output"
OUTPUT_VOICE = "ru-RU-DmitryNeural"  # Voz de salida, puedes cambiarla según tus necesidades

INPUT_TEXT_FILE = "texto.txt"
INPUT_LANGUAGE = "es-ES"  # Idioma de entrada, puedes cambiarlo según tus necesidades
INPUT_IMAGES_DIR = "imagenes"  # Directorio de imágenes de entrada
INPUT_IMAGES_NUMBER = 6  # Número de imágenes a generar
FONT_SIZE = 30  # Tamaño de fuente para los subtítulos

# Asegurar que los directorios de salida existan
os.makedirs(OUTPUT_AUDIO_DIR, exist_ok=True)
os.makedirs(OUTPUT_SUBTITLES_DIR, exist_ok=True)
os.makedirs(OUTPUT_VIDEO_DIR, exist_ok=True)
os.makedirs(OUTPUT_TRANSCRIPTS_DIR, exist_ok=True)

VIDEO_SIZE = (1280, 720)  # Tamaño estándar para YouTube HD

async def generar_audio(texto):
    """Genera un archivo de audio a partir de texto utilizando edge_tts y guarda en directorio con timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(OUTPUT_AUDIO_DIR, f"audio_{timestamp}.mp3")
    try:
        logging.info(f"Generando audio para el texto en '{output_file}'")
        voice = OUTPUT_VOICE # Voz en ruso, puedes cambiarla según tus necesidades
        communicate = edge_tts.Communicate(texto, voice)
        await communicate.save(output_file)
        logging.info(f"Audio generado exitosamente en '{output_file}'")
        return output_file
    except Exception as e:
        logging.error(f"Error al generar el audio: {e}")
        return None

async def esperar_archivo(file_path, timeout=60, stable_checks=5, check_interval=0.5):
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


def transcribir_audio(audio_path):
    """Transcribe un archivo de audio utilizando la librería whisper, guarda subtítulos y la transcripción completa."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(OUTPUT_SUBTITLES_DIR, f"subtitles_{timestamp}.srt")
    transcript_file = os.path.join(OUTPUT_TRANSCRIPTS_DIR, f"transcript_{timestamp}.txt")
    try:
        logging.info(f"Transcribiendo audio desde '{audio_path}'")
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

def crear_clips_de_subtitulos(subtitulos, tamano_video):
    """Crea clips de texto para los subtítulos."""
    clips_de_texto = []
    fuente = "fonts\\DejaVuSans.ttf"  # O usa una fuente instalada que soporte cirílico
    try:
        logging.info(f"Creando {len(subtitulos)} clips de subtítulos.")
        for (start, end), texto in subtitulos:
            texto_clip = TextClip(
                font=fuente,
                text=texto,
                font_size=FONT_SIZE,
                color='white'
            ).with_position('bottom').with_start(start).with_end(end)
            clips_de_texto.append(texto_clip)
        logging.info(f"Clips de subtítulos creados correctamente.")
        return clips_de_texto
    except Exception as e:
        logging.error(f"Error al crear los clips de subtítulos: {e}")
        return []

def crear_video_con_imagenes_y_subtitulos(lista_imagenes, audio_path, subtitulos):
    """Crea un video combinando imágenes, audio y subtítulos, y guarda en directorio con timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_video = os.path.join(OUTPUT_VIDEO_DIR, f"video_{timestamp}.mp4")
    audio_clip = None
    try:
        logging.info(f"Creando video '{output_video}' con {len(lista_imagenes)} imágenes y subtítulos.")
        audio_clip = AudioFileClip(audio_path)
        duracion_audio = audio_clip.duration
        num_imagenes = len(lista_imagenes)

        if num_imagenes > 0 and duracion_audio > 0:
            duracion_por_imagen = duracion_audio / num_imagenes
            clips_de_imagen = [
                ImageClip(img_path, duration=duracion_por_imagen).with_effects([Resize(new_size=VIDEO_SIZE)])
                for img_path in lista_imagenes
            ]
            video_principal = concatenate_videoclips(clips_de_imagen)
            video_principal = CompositeVideoClip([video_principal], size=VIDEO_SIZE)
            clips_de_subtitulos = crear_clips_de_subtitulos(subtitulos, VIDEO_SIZE)
            video_final = CompositeVideoClip([video_principal] + clips_de_subtitulos, size=VIDEO_SIZE)
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

async def main():
    """Función principal para la generación del video."""
    # Leer el texto a generar desde el archivo texto.txt
    try:
        with open(INPUT_TEXT_FILE, "r", encoding="utf-8") as f:
            texto_a_generar = f.read().strip()
    except Exception as e:
        logging.error(f"No se pudo leer el archivo {INPUT_TEXT_FILE}: {e}")
        return
    directorio_imagenes = INPUT_IMAGES_DIR
    nombres_imagenes = [f"imagen{i}.jpg" for i in range(1, INPUT_IMAGES_NUMBER+1)] + [f"imagen{i}.png" for i in range(1, INPUT_IMAGES_NUMBER+1)]
    lista_imagenes = [os.path.join(directorio_imagenes, nombre) for nombre in nombres_imagenes]

    # Control de existencia del directorio de imágenes
    if not os.path.exists(directorio_imagenes):
        logging.error(f"El directorio '{directorio_imagenes}' no existe.")
        return

    # Filtrar imágenes existentes
    lista_imagenes_existentes = [img_path for img_path in lista_imagenes if os.path.exists(img_path)]
    if not lista_imagenes_existentes:
        logging.error(f"No se encontraron imágenes en el directorio '{directorio_imagenes}'.")
        return

    # Generar audio
    audio_file_path = await generar_audio(texto_a_generar)
    if not audio_file_path:
        return

    # Esperar a que el archivo de audio se genere completamente
    logging.info(f"Esperando a que el archivo de audio '{audio_file_path}' se genere completamente.")
    if not await esperar_archivo(audio_file_path):
        logging.error(f"El archivo de audio '{audio_file_path}' no se generó completamente o se excedió el tiempo de espera.")
        return

    logging.info(f"Archivo de audio '{audio_file_path}' generado completamente. Procediendo con la transcripción.")

    # Transcribir audio
    subtitulos, subtitles_file_path = transcribir_audio(audio_file_path)
    if subtitulos is None:
        return

    # Crear el video
    video_file_path = crear_video_con_imagenes_y_subtitulos(lista_imagenes_existentes, audio_file_path, subtitulos)
    if video_file_path:
        logging.info(f"Proceso completado. Video guardado en: '{video_file_path}', Subtítulos (opcionalmente guardados en): '{subtitles_file_path}', Audio guardado en: '{audio_file_path}'")

if __name__ == "__main__":
    asyncio.run(main())