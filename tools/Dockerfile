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

FROM python:3.12-slim-bookworm

# fonts-noto-cjk instala en /usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc,
# que es exactamente la ruta por defecto de DEFAULT_FONT en kanji_metrics.py.
RUN apt-get update \
 && apt-get install -y --no-install-recommends fonts-noto-cjk \
 && rm -rf /var/lib/apt/lists/*

# Versiones fijadas, no flotantes. Son las que produjeron el kanji_content.json
# del 9 de septiembre de 2026; cambiarlas puede mover los decimales de las
# metricas y hay que hacerlo a proposito, no por un rebuild.
RUN pip install --no-cache-dir \
      "Pillow==12.2.0" \
      "numpy==2.4.4" \
      "scipy==1.17.1"

WORKDIR /repo

# Comprobacion de arranque: si la fuente no esta donde el script la busca, es
# mejor fallar al construir la imagen que producir metricas con otra tipografia
# sin que nadie se entere.
RUN python -c "\
from PIL import ImageFont; \
p='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'; \
ImageFont.truetype(p, 64); \
print('fuente CJK OK:', p)"

CMD ["python", "tools/kanji_metrics.py"]
