# Plan de desarrollo · alto de Events y cosméticas del monitor (D-F6-323 (4)–(5), D-F6-326 (4))

**Alineado hasta D-F6-329.** Escrito el vie 27 nov a las 17:55. **No se construye nada hasta el OK de Sebas.**

**Cuándo:** se construye y se integra **antes de las visitas del lun 30** (P06 a las 10:00), nunca con una sesión en curso.

**Fuentes:**
- `Claude outputs/Extracto_Diseno_Cosmeticas_27nov.md`: los Registros de Diseño web del 27 nov a las 12:15 (puntos 1–5) y a las 15:55 (puntos 1–4), y la regla del alto de más.
- `design-handoff/design-system.md`: el panel de decisiones en la línea 1170 y la línea de 60 Hz en la 983.

El plan anterior (vie 27) está archivado en `tasks/archive/viernes_27nov_plan.md`, con todas sus casillas hechas. `tasks/todo.md` no se toca, porque tiene casillas de otro trabajo; las casillas de este plan están al final.

**Fuera de este plan:**
- **La disposición *V1.13 layout with traces on*** (Sync dentro de System, la regla de colores detrás de una *i*, B1 y B2), que todavía no está validada (D-F6-323 (6), D-F6-321 (3)).
- **Los textos A, el cambio «Raw» → «Index» (D-F6-325) y B1.**

Por eso **a 1440 × 900, con TR encendido, Events sigue sin líneas** (D-F6-321 (1)). Este plan solo le da a Events el alto que sobra en pantallas más altas.

---

## Lo que dice el código hoy (leído a las 17:40, PC en `d87492c`)

**Alto de la página:**
- El monitor mide **900 px de alto fijos** (`Frame`, `LiveMonitor.tsx:402`: `h-[900px]`). A 1920 × 1080 sobran 180 px abajo (C-1 y C-2).
- Los paneles que ya crecen son *Adaptation decisions* (`flex-1`, `:251`) y *Events* (`flex-1`, `:281`). Los demás tienen el alto de su contenido.
- **Así que basta con que la página mida el alto de la ventana** (como mínimo 900 px) para que lo que sobra vaya solo a Events, en la columna derecha, y a Decisions, en la del medio. Ningún otro panel cambia de alto.

**Live indices cambia de alto según la etapa** (12:15, punto 1):
- En S7 la fila del nombre de cada franja tiene el valor en 24 px (`Readout`, `leading-7` = 28 px). En la ventana solo tiene el nombre, unos 20 px. Son 8 px por franja: **los 16 px** que midió Diseño web entre S5 (562) y S7 (578).
- En S8 a 1440, la línea de la ICA no cabe en la fila de chips y baja a otra fila: **los 24 px** de S8 (586).

**Lo demás:**
- **«Lead line (−1.5)»** va en la punta derecha (`IndicesWindow.tsx:121`), justo donde caen los puntos de decisión más recientes.
- **Eje de S7:** el filtro que escribí hoy quita la etiqueta que está a menos de 56 px de «Now». A 1440 eso quita «Trial 11» (punto 3).
- **Signo menos (12:15, punto 4):** el código ya usa «−» (U+2212) en las marcas, en el eje y en la línea guía. Las fuentes empaquetadas (Public Sans y JetBrains Mono, subconjunto *latin*) incluyen U+2212. **Lo más probable es que el dibujo de «−» en Public Sans a 9–10 px se parezca al guion.** Se comprueba carácter por carácter en el test (paso V) y no se cambia nada si sale bien.
- **Línea de 60 Hz:** dice «OK · 60 Hz, median of 8:» (`LiveMonitor.tsx:148`). El dibujo pone la marca y la palabra, y después «60 Hz, median of 8: [n] µV», sin el punto medio.
- **Decisiones:** a la derecha va `LAL MEDIUM → LOW` (`decisionLine`, `:244`).
  - El dibujo dice «**LAL down one step**» (600) y «No change» (400).
  - Lleva una **segunda línea** `caption` con la razón corta a la izquierda y «ESL Medium, LAL Medium → Low» a la derecha.
  - `/live` no manda la razón en palabras (solo `reason_code`).
- **El punto de decisión en S7 cae en «Now»** y la traza termina antes (15:55, punto 3). El punto va en `decided_elapsed_ms`, la hora de la respuesta. Las épocas que usó la ventana terminan 1,5 s antes (D-F6-188) y llegan ≈ 1,2 s después de terminar. Por eso el punto más nuevo siempre va ≈ 3 s por delante de la traza.

---

## Dependencias

```
H (alto de la página) ───────────────┐
I1 (mismo alto de franja + fila de chips) ─┤
I2 (etiqueta de la línea guía) ────────────┤
I3 (eje Trial) ────────────────────────────┼─→ V (test e2e + capturas) → RV (//review) → IN (integración, dist)
I4 (punto de decisión en su ensayo) ───────┤
D1 (línea de 60 Hz) ───────────────────────┤
D2 (palabras de las decisiones) ───────────┘
```

**Todo es página (`dashboard/`): no hay backend, ni migración, ni `live.py`.**
- Ninguna tarea depende de otra salvo V, que lo mide todo junto.
- Va en el worktree `NeuroAdaptativeVR-tr`, en la rama `feature/monitor-height`, que sale de `d87492c`.
- **No lleva interruptor:** son arreglos de un dibujo ya validado (como W el 26 nov), y se deshacen con `git revert`.

---

## Tareas

Cada tarea sigue el mismo ciclo: test que falla → código → Vitest completo → commit (enseño el mensaje primero) → `graphify update .`. **Las paradas están marcadas.**

### H · el alto de más va a Events y a Decisions (≈ 20 min) · D-F6-323 (4)
- En `Frame`, `h-[900px]` pasa a **`h-screen min-h-[900px]`**. El ancho no cambia (`w-full min-w-[1440px]`), ni las columnas 5 : 6 : 5, ni la barra de 88 px, ni la franja de 36 px.
- **A 900 px el resultado es idéntico al de hoy.** A 1080, Events y Decisions crecen y los demás paneles quedan igual.
- **Test (Vitest):** el `Frame` lleva `h-screen` y `min-h-[900px]`. El alto real lo mide V.

### I1 · el mismo alto de franja en S7 y en la ventana, y la línea de la ICA en la fila de chips (≈ 30 min) · 12:15, punto 1
- La fila del nombre de cada franja mide **28 px fijos** en los dos modos. En la ventana se queda vacía a la derecha, sin valor (como pide el dibujo).
- Fila de chips sin salto de línea (`flex-nowrap`, separación de 6 px).
- **Si la línea de la ICA no cabe, se recorta con «…»** y el texto entero va en `title`. A 1920 cabe siempre.
  - A 1440 caben «ICA applied at 00:09:15, r 0.83» junto a «Raw, no decisions after S7». **«ICA not found at …, rule (2) from here» junto a «▲ Rule: (2) fallback» no cabe entera.**
  - **Parada I1:** ¿Diseño web acepta los «…» a 1440 en ese caso? Si no, que diga qué cede, por ejemplo el chip de referencia más corto. No lo decido yo.
- **Test:** Vitest comprueba que los dos modos tienen la misma clase de alto en la fila del nombre, y que la fila de chips no salta de línea. V mide en el navegador que *Live indices* termina en el mismo píxel en S5, S7 y S8.

### I2 · «Lead line (−1.5)» legible (≈ 15 min) · 12:15, punto 2
- La etiqueta pasa **al extremo izquierdo de la franja de S7**, donde no hay decisiones: empiezan en el ensayo 3.
- Lleva **halo** de `--color-surface` (`paint-order: stroke`, como las etiquetas de fase y de las trazas) y se dibuja encima de la traza.
- **Test (Vitest):** la etiqueta está anclada a la izquierda, lleva el halo y va después de los puntos en el SVG, para quedar encima.

### I3 · el eje de S7 muestra el último ensayo (≈ 20 min) · 12:15, punto 3
- Se muestran las etiquetas de los ensayos impares. Si una choca con «Now», o dos quedan a menos de 44 px entre sí, **se quita la más antigua** (primero «Trial 1»), nunca la más reciente.
- **Test (Vitest):** con los ensayos 1–11 en 452 px aparece «Trial 11», y no hay dos etiquetas a menos de 44 px ni ninguna encima de «Now».

### I4 · el punto de decisión en su ensayo (≈ 25 min) · 15:55, punto 3 · **parada I4**
- **Propuesta:** la x del punto pasa a ser **el centro de las épocas de su ensayo** (`trial_id` de la decisión).
  - Si todavía no hay ninguna época de ese ensayo, va en `decided_elapsed_ms − 1,5 s`, el fin de lo que leyó el motor (D-F6-188).
  - Así el punto queda sobre la traza y no en «Now».
  - **Pregunta para Sebas y Diseño web:** ¿«en su ensayo» quiere decir esto? Si prefieren la x por número de ensayo (como el tramo S7 de D-F6-280), se cambia la fórmula y lo demás queda igual.
- **Test (Vitest):** una decisión del ensayo 5, con épocas de ese ensayo, cae en su centro. Sin épocas, cae 1,5 s antes de su hora.

### D1 · la línea de 60 Hz como en el dibujo (≈ 10 min) · 15:55, punto 1
- Queda así: la marca, «OK» o «Watch», y después «60 Hz, median of 8: **[n] µV**», sin el « · ».
- **Test (Vitest):** el texto ya no lleva « · », y la palabra y la cifra están.

### D2 · las decisiones en palabras (≈ 40 min) · 15:55, punto 2
- **A la derecha:** «**ESL up one step**», «**LAL down one step**» o «No change». El sentido sale del orden LOW < MEDIUM < HIGH. Si alguna vez fueran dos niveles, diría «two steps». Si el nivel no se reconoce, queda el texto de hoy.
- **Segunda línea**, `caption`, a la derecha: «ESL Medium, LAL Medium → Low» en un cambio, o «ESL Medium, LAL Low» si no cambia nada.
  - **La razón corta a la izquierda no entra en este plan:** `/live` solo manda `reason_code`. Traerla exige tocar el backend y su test (≈ 20 min más).
  - **Pregunta para Sebas:** (a) la segunda línea sin razón ahora, y la razón con los textos A (**recomendado**); o (b) también la razón ahora, con el cambio de backend.
- **Con la segunda línea, cada fila mide ≈ 16 px más:** a 900 px caben unas 4 decisiones en vez de 6. A 1080 se recupera con H.
- **Test (Vitest):** el cambio de LAL MEDIUM → LOW dice «LAL down one step» y «ESL Medium, LAL Medium → Low». «No change» dice «ESL Medium, LAL Low». Un nivel desconocido no rompe nada.

### V · test e2e y capturas (≈ 45 min) · **parada V**
- **Nuevo `dashboard/tests/e2e/monitor-layout.spec.ts`:**
  - con la API simulada por rutas: datos inventados (`DEMO01`), TR encendido con bins sintéticos, S5, S7 y S8;
  - corre contra `vite preview` del worktree en el puerto 5199. Para eso, `playwright.config.ts` lee `PW_BASE_URL` (una línea; por defecto sigue en 5300).
- **Comprueba:**
  - **1440 × 900 frente a 1920 × 1080:**
    - Signal quality, System, Live indices, Sync y Channel traces tienen **el mismo alto** (±1 px);
    - **Events crece ≈ 180 px** y Decisions crece;
    - no hay scroll en ninguno.
  - **Live indices termina en el mismo píxel en S5, S7 y S8**, a 1440 y a 1920.
  - **Ningún guion ASCII delante de una cifra** en las marcas, el eje, la línea guía ni las trazas. Es la comprobación del punto 4.
  - «Trial 11» se ve a 1440.
- **Capturas para Diseño web** en `design-handoff/monitor/`, con el commit en el borrador:
  - `Monitor_alto_completo_1920x1080_S7_<fecha>.png` y `…_S5_<fecha>.png`;
  - `MI_fuera_S7_S8_1440x900_<fecha>.png`, para el punto 1.
- **Parada V:** Sebas mira las capturas y, si quiere, se las pasa a Diseño web.

### RV · //review (≈ 20 min)
- Un revisor aparte revisa el diff de la rama.
- Lo primero que mira es que a 900 px no cambie nada fuera de lo pedido, y que un nivel o un `trial_id` raros no rompan el panel.

### IN · integración (≈ 15 min) · antes del lun 30 a las 9:00, sin sesión en curso
1. Comprobar que no hay ninguna sesión en curso.
2. Unir la rama a `phase/4-eeg-aura`.
3. Vitest completo y el e2e nuevo contra `:5300`.
4. `npm run build` de `dist`.

**No hace falta:** reiniciar el backend, tocar `.env` ni hacer `pg_dump` (no se toca la base). El backend no cambia salvo que en D2 se elija la opción (b).

**`git status` limpio al terminar** (`preflight` falla si no).

---

## Riesgos

- **D2 deja menos decisiones visibles a 900 px** (de 6 a ≈ 4). Es lo que pide el dibujo. Si Sebas prefiere 6, la segunda línea puede esperar a la disposición nueva.
- **I1 puede recortar la línea de la ICA a 1440** en las sesiones con la regla (2) (parada I1).
- **I4 cambia dónde se ve el punto, no lo que significa:** el valor, la palabra y el ensayo no cambian. Si la respuesta de la parada I4 es otra, solo cambia la fórmula.
- **Las visitas del lun 30 corren con este código.** Se declara en el registro de cada una (D-F6-322 (6)).

**Tiempo:** ≈ 3 h 20 min con las paradas. Construido el sáb 28 o el dom 29 con el OK de Sebas, o el lun 30 de 7:00 a 9:00 como último recurso.

---

## Casillas

- [x] 0 · OK de Sebas al plan; respuestas de I1 (los «…»), I4 (dónde va el punto) y D2 (con razón o sin ella)
- [x] H · alto de la página · Vitest · commit
- [x] I1 · mismo alto de franja y fila de chips · Vitest · commit
- [x] I2 · línea guía legible · Vitest · commit
- [x] I3 · eje Trial · Vitest · commit
- [x] I4 · punto de decisión en su ensayo · Vitest · commit
- [x] D1 · línea de 60 Hz · Vitest · commit
- [x] D2 · decisiones en palabras · Vitest · commit
- [x] V · e2e a 1440 y a 1920, comprobación del signo menos, capturas en `design-handoff/monitor/`
- [x] RV · //review y arreglos
- [x] IN · integración, `dist`, `git status` limpio, sin sesión en curso · antes del lun 30 a las 9:00
