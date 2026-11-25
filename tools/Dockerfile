# Entorno reproducible para las herramientas de contenido kanji.
#
# Por que existe: las metricas de complejidad perimetrica y de confusabilidad
# grafica se calculan renderizando los glifos, asi que **dependen de la
# tipografia**. Correr el script con otra fuente da otros numeros y puede
# voltear un chequeo de banda. Fijar la fuente en una imagen es lo que hace que
# el resultado sea el mismo para cualquiera que lo corra, hoy o dentro de un
# ano, y es lo que permite defender los numeros si el trabajo se publica.
#
# El segundo motivo es mas simple: la maquina de desarrollo es Windows y no
# tiene ni las dependencias ni la fuente en la ruta que el script espera. Sin
# esto, la regla "regenerar en el mismo commit que cambia un kanji" seria una
# instruccion que nadie del equipo puede cumplir.
#
# Uso desde la raiz del repositorio:
#   docker compose run --rm kanji-tools python tools/kanji_metrics.py --export
#
# El servicio esta bajo el perfil "tools", asi que `docker compose up` no lo
# levanta: es una herramienta de un solo disparo, no un servicio.

# Misma base que backend/Dockerfile, a proposito: si el backend ya se
# construyo, esta imagen esta en la cache local y no hay nada que descargar.
# La primera version fijaba python:3.12-slim-bookworm, que es OTRO tag y por
# tanto otra descarga completa -- justo lo que no conviene en una red donde el
# CDN de Docker falla.
FROM python:3.12-slim

# fonts-noto-cjk instala en /usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc.
#
# Ese .ttc ya NO es la fuente con la que se calcula. Es el origen del que
# tools/extract_board_font.py saca la cara japonesa hacia
# unity-client/Assets/Fonts/, y esa cara extraida es lo que usan tanto
# kanji_metrics.py como el TMP_FontAsset de Unity. Motivo, en corto: un .ttc es
# una coleccion de varias caras --PIL abre el indice 0, TMP elige por su
# cuenta-- y ademas Unity no puede leer una ruta dentro de esta imagen. Una
# metrica de complejidad calculada sobre una cara distinta de la que ve el
# participante es un numero que no describe el experimento.
#
# La ruta es la misma en bookworm y en trixie; si una version futura de Debian
# la moviera, la comprobacion del final de este archivo lo detecta al construir.
RUN apt-get update \
 && apt-get install -y --no-install-recommends fonts-noto-cjk \
 && rm -rf /var/lib/apt/lists/*

# Versiones fijadas, no flotantes. Son las que produjeron el kanji_content.json
# del 9 de septiembre de 2026; cambiarlas puede mover los decimales de las
# metricas y hay que hacerlo a proposito, no por un rebuild.
#
# fonttools entra el 10 de septiembre y solo lo usa extract_board_font.py: parte
# el .ttc y guarda una cara. No participa del calculo de ninguna metrica.
RUN pip install --no-cache-dir \
      "Pillow==12.2.0" \
      "numpy==2.4.4" \
      "scipy==1.17.1" \
      "fonttools==4.62.1"

WORKDIR /repo

# Comprobacion de arranque: si la fuente no esta donde el script la busca, es
# mejor fallar al construir la imagen que producir metricas con otra tipografia
# sin que nadie se entere.
RUN python -c "\
from PIL import ImageFont; \
p='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'; \
ImageFont.truetype(p, 64); \
print('fuente CJK OK:', p)"

# Y que fonttools pueda abrirla como coleccion, que es lo que hace el extractor.
RUN python -c "\
from fontTools.ttLib import TTCollection; \
c=TTCollection('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'); \
print('caras en el .ttc:', len(c.fonts))"

CMD ["python", "tools/kanji_metrics.py"]
