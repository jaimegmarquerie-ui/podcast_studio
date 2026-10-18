# Podcast Studio

**Autor:** Jaime Gárate · Proyecto 1 del bootcamp AI Consulting de Ironhack

Podcast Studio convierte el texto de un libro (una ficha, una reseña o un guion) en un podcast corto: **pega el texto, elige voz y estilo, y escucha el resultado**. Es una aplicación local con interfaz web hecha con Gradio.

## Qué problema resuelve

Mucha gente no lee porque no sabe qué leer: no sabe qué libro le puede gustar ni por dónde empezar. Elegir a ciegas, a partir de una reseña larga o de una ficha de editorial, cuesta tiempo y esfuerzo. Podcast Studio convierte ese texto en un audio de 2 a 5 minutos, con una voz y un tono que encajan con el libro, para que cualquiera pueda hacerse una idea de qué trata y decidir si quiere leerlo, mientras hace otra cosa.

El caso de uso con el que se ha probado es el podcast ficticio *One Week, One Book*, con el episodio sobre *Death and the Gardener* de Georgi Gospodinov (texto en `examples/mi_guion.txt`).

## Cómo funciona

```
Texto del libro  ->  Limpieza (Python)  ->  Guion con IA (Gemini)  ->  Voz (Gemini TTS)  ->  Audio
   (interfaz Gradio)    data_processor        llm_processor              tts_generator
```

1. **Entrada** (`src/data_processor.py`): lee el texto (pegado o desde un archivo), lo limpia, detecta campos como título o autor y devuelve un diccionario estándar `{"metadata": ..., "text": ..., "word_count": ...}`. Si el texto es demasiado corto, avisa al usuario.
2. **Transformación** (`src/llm_processor.py`): un modelo de Gemini escribe un guion de podcast en inglés a partir del texto. El usuario elige el estilo (conversacional, reflexivo y literario, o resumen rápido). Las instrucciones piden usar solo información del texto y no inventar datos ni citas.
3. **Audio** (`src/tts_generator.py`): Gemini TTS convierte el guion en un archivo de audio con la voz elegida (9 voces disponibles). Si falla, la aplicación prueba edge-tts y, como último recurso, gTTS, y muestra qué voz se usó.
4. **Interfaz** (`src/main.py`): página de Gradio que une los tres pasos y muestra estado, audio y guion.

## Requisitos

- Python 3.8 o superior (probado con Python 3.11).
- Una clave de la API de Gemini (gratuita), que se crea en [Google AI Studio](https://aistudio.google.com/apikey).
- Conexión a internet.

## Instalación

1. Clona el repositorio y entra en la carpeta:

   ```bash
   git clone <URL-DEL-REPOSITORIO>
   cd podcast_studio
   ```

2. Crea y activa un entorno de Python (con conda o con venv). Ejemplo con venv en Windows:

   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. Instala las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

4. Crea un archivo llamado `.env` en la carpeta principal del proyecto con tu clave (el archivo no se sube a GitHub):

   ```
   GEMINI_API_KEY=tu_clave_aqui
   ```

   Puedes comprobar que se lee bien, sin mostrarla, con:

   ```bash
   python src/main.py --check-key
   ```

## Uso

Desde la carpeta principal del proyecto:

```bash
python src/main.py
```

Abre en el navegador la dirección que aparece en el terminal (normalmente `http://127.0.0.1:7860`) y:

1. Pega el texto del libro, sube un archivo `.txt`, `.md` o `.pdf`, o carga uno de los dos ejemplos con los botones.
2. Elige la **voz** y el **estilo y duración**.
3. Pulsa **Generate podcast** y espera entre 1 y 3 minutos.
4. Escucha el audio y lee el guion generado. Los archivos se guardan en la carpeta `outputs/`.

Para probar el flujo completo sin abrir la interfaz: `python src/main.py --test`.

## Pruebas automáticas

Hay pruebas pequeñas que no necesitan internet ni clave (simulan los servicios externos):

```bash
python -m unittest discover tests
```

Comprueban la lectura de la ficha y de archivos, el rechazo de textos cortos, el contenido del prompt y la cadena de respaldo del audio.

## Ejemplo incluido

En la carpeta `examples/`:

| Archivo | Contenido |
|---|---|
| `mi_guion.txt` | Texto de entrada sobre *Death and the Gardener* |
| `example_script_death_and_the_gardener.txt` | Guion generado por la IA (estilo reflexivo) |
| `example_podcast_death_and_the_gardener_sulafat.wav` | Audio generado con la voz Sulafat (unos 4 minutos) |
| `sample_sheet.txt` | Ficha de ejemplo inventada, para pruebas |

## Decisiones técnicas

- **Gemini para el guion y para la voz:** una sola clave y un solo proveedor para los dos pasos, con nivel gratuito.
- **Voz cálida por defecto (Sulafat):** el libro de ejemplo trata del duelo y la memoria, y se eligió una voz descrita como cálida y un estilo reflexivo. Se compararon dos voces (Achernar y Sulafat) escuchándolas.
- **Cadena de respaldo para el audio:** los servicios de voz pueden fallar. Si Gemini TTS no responde, se usa edge-tts y después gTTS, y la interfaz indica qué voz se usó.
- **Errores controlados:** cada paso del flujo tiene su propio `try/except`. El usuario ve un mensaje claro en el campo *Status* (texto demasiado corto, fallo de la IA, fallo del audio) en lugar de que la aplicación se rompa.
- **Estructuras de datos:** diccionarios para la ficha y para las listas de voces y estilos.

## Costes y límites

- **Gemini API (guion y voz):** se usa el nivel gratuito. En ese nivel, Google puede usar el contenido enviado para mejorar sus productos; conviene no pegar datos privados. Los límites exactos de peticiones del nivel gratuito para voz no se han verificado.
- edge-tts y gTTS son servicios gratuitos y no oficiales que pueden fallar o cambiar sin aviso. En las pruebas, edge-tts devolvió un error 403, y por eso es solo un respaldo.
- El audio de Gemini TTS se guarda en formato WAV (24 kHz, mono), que pesa más que un MP3.

## Limitaciones

- El guion se genera siempre en inglés, aunque el texto de entrada esté en otro idioma.
- La aplicación es local; no está desplegada en internet.
- Acepta texto pegado o archivos `.txt`, `.md` y `.pdf` con texto. Los PDF escaneados (imágenes) y las direcciones web no están soportados.
- La interfaz está hecha solo con Gradio (sin servidor aparte con FastAPI).

## Estructura del proyecto

```
podcast_studio/
├── src/
│   ├── data_processor.py   # entrada (texto, .txt, .md, .pdf) y limpieza
│   ├── llm_processor.py    # guion con Gemini
│   ├── tts_generator.py    # voz con Gemini TTS y respaldos
│   └── main.py             # flujo completo e interfaz Gradio
├── tests/                  # pruebas automáticas
├── examples/               # textos y audio de ejemplo
├── requirements.txt
├── README.md
└── .env                    # clave de la API (no se sube a GitHub)
```

## Mejoras futuras

- Aceptar direcciones web y PDF escaneados (con OCR) como entrada.
- Guiones en más idiomas y voces para cada uno.
- Convertir el audio final a MP3 para que pese menos.
- Dos voces conversando, como en un podcast de dos presentadores.

## Nota sobre el desarrollo

El proyecto se desarrolló con la ayuda de un asistente de IA (Claude) como tutor y apoyo de programación, y todas las pruebas se hicieron en mi equipo con mi propio texto del libro.
