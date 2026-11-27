# Plan de desarrollo · vie 27 nov 2026

**Alineado hasta D-F6-322.** Escrito el vie 27 a las 11:35; **aprobado con notas por D-F6-320** (textos de §7.6 en `Claude outputs/Extracto_UI_Indices_fuera_S7_27nov.md`; paso a la (2) a mitad de sesión, provisional: «Rule (2) from {hh:mm:ss}»; al terminar la prueba, reproductor cerrado y ningún `AURA` falso antes de P04; SY0 en paralelo con un subagente; `TEST2701` en `STATIC`).
El plan anterior (semana del 16 al 26 de noviembre) está archivado en `tasks/archive/semana_16nov_plan.md`.
`tasks/todo.md` no se toca: tiene 123 casillas de otro trabajo. La lista de casillas de hoy está al final de este archivo.

**El día (D-F6-318):**
- **Mañana:** construir MI fuera de S7 y el FAIL de `preflight` en el worktree, con sus tests y la //review.
- **Antes de las 14:30:** integrarlos, con `dist` reconstruido y sin ninguna sesión en curso.
- **De 14:30 a 16:00:** prueba sintética del monitor con el XDF de P03.
- **17:30:** P04 (`STATIC`), con M1b, MI y TR encendidos.

**Reglas de hoy:**
- Cada parte se cierra así: tests, commit (enseño el mensaje primero), `graphify update .` y **parada**.
- Nada se integra, se reinicia ni corre pesado a partir de las 16:00 (kit de P04).
- Los interruptores se cambian solo sin sesión en curso: `backend/.env`, luego `docker compose up -d backend`, y se comprueba con `printenv`.
- Los scripts de la prueba sintética van en el scratchpad, nunca en el repo. El XDF no sale de la PC.

**Lo que dice el código hoy (leído a las 11:00–11:30, PC en `995f0aa`):**
- **Backend.** `_session_trace` (`backend/app/api/routes/research.py:570`) manda cada época en ln en S1–S4 y S6, y en z en S5 (frente a S4) y de S7 a S9 (frente a la referencia). Va detrás de `MONITOR_LIVE_INDICES`, que está en `true`.
- **Página.** `SessionIndices.tsx` dibuja la sesión entera por franjas fijas (`SLOTS`). Cada bloque en ln se autoescala con sus propios datos (`Strip`, `range`). La línea de la ICA está dentro de la gráfica, en S6.
- **ICA.** El dict `ica` no guarda la hora del ajuste. El ajuste ocurre cuando llegan muestras hasta la entrada a S6 + `EDGE_S` (`live.py:98-103`).
- **`preflight`.** `check_lsl` (`backend/app/eeg/preflight.py:79`) da `WARN` con «no AURA on this PC yet».
- **El motor** solo se carga si la condición es adaptativa: `_load_adaptation` (`websocket.py:248`), al abrir el WebSocket.
- **`live.py`** toma el id de la sesión como argumento y no compara el id que llevan los marcadores.
- **El worktree** `NeuroAdaptativeVR-tr` sigue en `feature/monitor-traces` (`45a5633`), por detrás de `995f0aa`.
- **Los textos de UI/UX §7.6 no están en el espejo.** `Contenido_UI_Monitor_Indices.md` del espejo es del 20 nov y termina en §6. Los textos de abajo salen de `design-system.md` (V1.13 *Live indices outside S7*, Validated) y del artboard validado `LiveIndicesWindow.dc.html`. Ver la parada 0.

**Grafo de dependencias:**
```
Parada 0 (OK de Sebas + textos §7.6)
 ├─ MI-B (backend) ─→ MI-P (página) ─┐
 ├─ PF (preflight) ──────────────────┼─→ RV (//review) ─→ IN (integración, dist) ─→ SY (prueba sintética) ─→ P04
 └─ SY0 (reproductor, scratchpad, sin LSL ni base) ──────────────────────────────┘
```
- SY0 no depende del código: un subagente puede escribirlo en paralelo mientras yo hago MI (lo propongo; Sebas decide en la parada 0).
- SY corre aunque MI no llegue: entonces se prueba con la vista anterior de MI.

---

## Parada 0 · 11:35–11:45 · OK de Sebas

- Sebas aprueba el plan, o lo cambia.
- **Textos §7.6:** Sebas me pasa `Contenido_UI_Monitor_Indices.md` §7.6 (o lo exporta al espejo). Si no llega a las 12:40, cuando empieza MI-P, uso los textos de `design-system.md` y del artboard validado, y lo dejo declarado en el borrador. Ya dejé la duda escrita para PM (duda 1).
- **Condición de la sesión `TEST`:** `STATIC` (recomendado) o la otra opción de SY2.
- **Subagente para SY0:** sí o no.

---

## 1 · MI fuera de S7 (D-F6-308 (3), D-F6-309 (4), D-F6-312 (3)) · ≈ 2 h 15 min · 11:45–14:00

**Interruptor nuevo: `MONITOR_INDICES_WINDOW`** (`backend/.env`, lo lee solo el backend, apagado por defecto).
- **Apagado:** la respuesta y la página quedan como hoy, byte a byte. Es la vista de D-F6-280.
- **Encendido:** la vista nueva (S7 sola en z, ventana de 20 s en ln fuera de S7).
- Solo funciona si `MONITOR_LIVE_INDICES` también está en `true`.
- Así, en P04 se puede quedar con la vista anterior sin quitar código (D-F6-318 (3)).

### MI-B · backend (≈ 40 min) · 11:45–12:25

`config.py` lleva `monitor_indices_window: bool = False`, con un comentario como el de los otros interruptores.

Con el interruptor encendido, `_session_trace` añade, sin tocar lo que ya manda:
- **en cada época:** `end_ms`, y `ln_ei` y `ln_theta`, el ln del índice. Son `null` si la época es POOR o si el valor es ≤ 0. Sale de `eeg_epochs`, igual que hoy, sin cálculo nuevo de EEG;
- **en `ica`:** `at_ms`, el momento del ajuste en ms de sesión = entrada a S6 + `EDGE_S`. Es un atajo: el dict de `live` no guarda la hora. Va con el comentario `shortcut:`, y se mejora si `live` llega a escribir la hora;
- **en la traza:** `"view": "window"`, para que la página sepa qué vista dibujar.

Los campos `ei` y `theta` que ya existen siguen igual: en S7, z frente a S6, que es lo que usa la vista de S7.

**Tests (pytest, `test_research_live.py`):**
- con el interruptor apagado, el snapshot es igual que antes (ya hay un test así; se amplía para el interruptor nuevo);
- con el interruptor encendido, `ln_*` = `log(valor)` en S5 y en S8 (hoy en esos estados se manda z), y es `null` en POOR;
- `ica.at_ms` = S6 + `EDGE_S`;
- con `MONITOR_LIVE_INDICES` apagado, no sale nada aunque el interruptor nuevo esté encendido.

### PF · `preflight`: «no AURA on this PC yet» pasa a FAIL (D-F6-315 (4)) · ≈ 15 min · 12:25–12:40

- En `preflight.py:79`, `WARN` pasa a `FAIL`. El texto no cambia.
- `main()` ya sale con FAIL si hay alguno, así que no hay que tocarlo. Lo compruebo leyendo `main()`.
- **Test (`test_eeg_preflight.py`):** `check_lsl([], host)` da `FAIL` con «no AURA on this PC yet». Si algún test actual espera `WARN`, se corrige en el mismo commit.
- **Efecto en el kit:** desde la integración, si `preflight` corre antes de LSL Stream Out, sale FAIL. Eso es justo lo que se busca: LSL Stream Out es el paso 1 (D-F6-314 (7)).

### MI-P · página (≈ 1 h 10 min) · 12:40–13:50

El trabajo va en `SessionIndices.tsx`, más el test. Si `s.view === 'window'` se usa la vista nueva; si no, el componente de hoy sin cambios.

**Etapa actual S7:** S7 sola, en z.
- La franja va desde el inicio de S7 (x 0) hasta ahora (borde derecho) y se llena a medida que avanza S7.
- Lleva `z` arriba, la zona Normal entre ±1 con sus líneas, la línea roja discontinua en −1,5 con «Lead line (−1.5)», y la traza en sus colores validados.
- Lleva los puntos de decisión con su palabra y el valor junto al nombre del índice, como el tramo S7 validado.
- Sin tramos de S1–S6 y sin eje de etapas. El eje dice «Trial 1, 3, 5, 7, 9, 11» y «Now».
- Una exclusión de canal después de S6 deja su línea vertical dentro de S7.
- No hay botón «Whole session» (D-F6-309 (4) (e)).

**Fuera de S7 (S4–S6, S8–S9 y la sesión terminada):** ventana de 20 s en ln.
- Escala ln fija para todos: Engagement Index de −3,0 a 0,0 y Theta (Fz) de −3,5 a −0,5.
  - Marcas en los extremos y en el medio («−3.0, −1.5, 0.0» y «−3.5, −2.0, −0.5»), en mono 9, en un margen de 36 px, con sus líneas de 1 px, y `ln` arriba.
  - **Sin autoescala:** se quita el `range` que se ajusta a los datos. Un valor fuera de la escala se recorta al borde.
- Sin z, sin zona Normal, sin ±1 ni −1,5, sin Low / Normal / High, sin el valor junto al nombre y sin «EEG counted».
- **Eje:** «−20 s, −16, −12, −8, −4» y «Now», con una línea de 1 px en Now y una rejilla cada 4 s.
  - «Now» = el ms de sesión del reloj de la página, el mismo `useClock` del monitor.
  - El borde izquierdo es Now − 20 s.
- **Un punto por época** (4,4 px), en el centro de la época (`(start_ms + end_ms)/2`). Salen 7 u 8 puntos.
  - Están unidos por la traza de 1,25 px, en su color: OK, no válida, o gris (ojos cerrados o ICA ajustándose).
  - La traza no se une a través de una línea de etapa.
- **Líneas de fase:** una línea de 1 px en cada cambio de etapa que cae en la ventana, con el nombre («S5», «S6», «S8», «S9») arriba de la franja del EI, sobre un halo `--color-surface`. Salen de `stages`, que ya llega.
- Tamaño: el de S7, a todo el ancho y alto del panel (EI 76 px, Theta 64 px, D-F6-309 (4) (a)).
- Hasta el fin de S3 se muestra «Indices from the end of S3», como hoy.

**Fila de chips (§7.6 y §2):**
- **Regla, desde S6:** «Rule: ICA» o «Rule: (2) fallback».
- **Referencia:**

| Etapa | Chip |
| --- | --- |
| S1–S3 | «Raw, no reference yet» |
| S4 | «Raw, S4 baseline» |
| S5 | «Raw, no decisions yet» (en ln, ya no z frente a S4) |
| S6 | «Building reference (S6)» |
| S7 | «z vs S6 (ICA)» / «z vs S6 (rule 2)» / «z vs S4 eyes open (fallback)» |
| S8–S9 | «Raw, no decisions after S7» |

- **Línea de estado de la ICA:** texto `caption` en `--color-text-secondary`, al final de la fila, con su marca:
  - «Fitting ICA» con un anillo hueco;
  - «ICA applied at hh:mm:ss, r 0.79» con un punto Lagoon;
  - «ICA not found at hh:mm:ss, rule (2) from here» con un triángulo ámbar.

  La hora sale de `ica.at_ms` en el reloj de sesión. La línea queda escrita hasta el final, también en S7, y ya no hay ninguna línea de la ICA dentro de las franjas.
  - **Caso de cambio a la (2) a mitad de sesión** (`switched_to_nosound_at`): el texto exacto es de §7.6. Si no llega, uso el chip «Rule: (2) fallback» y la línea «ICA applied at …» sin cambiar, y lo declaro.
- «EEG counted in k of n» pasa al final de la línea «Updates with each epoch, every 2.5 s.», solo en S7.
- **Nombres accesibles:** «{index}, last 20 seconds, log values» fuera de S7, y «{index}, stage S7, z against S6» en S7.

**Tests (Vitest, `LiveMonitor.test.tsx`, con fixtures):**
- **Con `view` ausente:** se dibuja la vista de hoy. Los tests actuales pasan sin cambios.
- **S5, ventana:** solo las épocas de los últimos 20 s.
  - Un punto con ln −1,5 cae a media altura del EI y uno con −3,5 queda al borde de Theta.
  - Hay una línea de fase en S5 con su nombre.
  - La traza no se une a través de esa línea.
- **S7:** sin tramos de S1–S6, eje «Trial».
- **Chips** por etapa, y **la línea de la ICA** en sus tres estados, con la hora.
- **Nombres accesibles.**

**Capturas (Playwright, con el checkpoint del monitor que ya existe) · 13:50–14:00:**
- S5, S7 y S8, a 1440 × 900 y 1920 × 900, en claro.
- Sin scroll, y con el mismo aspecto que `Indices_en_vivo_fuera_de_S7_1440x900_claro.png` y `Indices_en_vivo_S7_1440x900_claro.png`.
- Se las paso a Sebas.

**Parada MI:** Sebas mira las capturas. Si algo no cuadra con el dibujo, se anota, y MI entra igual con su interruptor apagado.

**Riesgos de MI:**
- **Tiempo:** son ≈ 2 h 15 min para 2 h 15 min de hueco. Si a las 13:50 la página no está, MI-P no se integra (ver IN).
- **Los textos de §7.6,** si los de UI/UX difieren de los del dibujo.
- **El reloj.** Si el «Now» del navegador va por delante de la última época más de lo esperado (≈ 3,7 s), los puntos se ven corridos a la izquierda. Es lo que dice el dibujo, no un error.

---

## 2 · //review e integración · 14:00–14:30 (D-F6-318 (1))

### RV · //review (≈ 15 min) · 14:00–14:15
- **Alcance:** el diff del worktree frente a `995f0aa` (MI-B, PF y MI-P).
- Se arregla lo que importa: que con el interruptor apagado todo quede igual, y que no se rompa ningún camino de la visita.
- Lo demás se anota en el borrador.

### IN · integración (≈ 15 min) · 14:15–14:30, sin sesión en curso
1. `pg_dump` completo de respaldo en la PC. Hoy no hay migración, pero se hace igual: son 2 min.
2. La rama del worktree entra en `phase/4-eeg-aura`.
3. pytest completo y Vitest, dentro del contenedor como siempre.
4. `npm run build` de `dist`.
5. `docker compose up -d backend`, con `MONITOR_INDICES_WINDOW=true` para la prueba sintética.
6. `/health/db`, `printenv` de los interruptores y `git status` limpio.

**Parada IN:** cifras de pytest y Vitest, el commit integrado y los interruptores.

**Puntos de corte:**
- **A las 14:15, MI-P sin terminar o con la review abierta:** se integra solo PF, más MI-B con el interruptor apagado si pasó la review. Si no, ni eso. MI-P se queda en la rama. P04 va con la vista anterior de MI.
- **Algún test falla después de unir la rama:** no se fuerza nada. Se deshace la unión con `git reset --hard 995f0aa` sobre la rama de la PC, que es destructivo: lo hago solo con el OK de Sebas en ese momento. Se integra solo lo que pase.
- **Nada se integra después de las 14:30.** Lo que no llegue, va después de P04 o el lun 30, con número.

**Riesgos:** si el pytest completo tarda más de lo normal (≈ 5 min), se come el margen. Y si hay que reconstruir `dist` dos veces, son 2 min más.

---

## 3 · Prueba sintética del monitor con el XDF de P03 (D-F6-318 (2)) · 14:30–16:00

**Para qué sirve:**
- ver todo el monitor en vivo, con todos los paneles;
- medir C2b y la parte de C4 que se puede medir sin Unity.

**No mide `FRAME_HITCH`, porque no hay Unity.**

**Fuentes, solo lectura:**
- el XDF de P03: `C:\Users\drdom\Documents\Pruebas_EEG\sub-P03\ses-9b0de1c3\eeg\sub-P03_ses-9b0de1c3_task-MULTIMODALADAPTIVE_run-1_eeg.xdf`. Se lee en su sitio, sin copiarlo;
- los eventos de `9b0de1c3` en `session_events`: 280 filas, de las cuales 20 son `ADAPTATION_DECISION`, 1 `ADAPTATION_OUTCOME`, 1 `EEG_STATUS` del backend y 1 `EEG_BASELINE_RESULT` de `baseline.py`;
- su único `VALIDATION_EVENT`, en `system_validation_events`.

**Duración de P03:** 14,1 min (de 11:23:22 a 11:37:28 UTC).

### SY0 · el reproductor (≈ 40 min) · scratchpad · 11:45–12:30, en paralelo con MI si Sebas acepta el subagente; si no, 13:50–14:30 y MI-P se recorta

Parte de `pub.py` de SIM5, que ya mandaba `AURA` y `UnityMarkers` de un XDF a 1×. Se le añade el envío de los eventos por el WebSocket, con el mismo reloj. Un solo proceso: `replay_p03.py`.

**LSL, igual que SIM5:**
- dos salidas, `AURA` (8 canales, 250 Hz) y `UnityMarkers`;
- `source_id` = `REPLAY_P03_AURA` y `REPLAY_P03_MARKERS`, nunca `synthetic-aura`;
- espera a que haya un consumidor en las dos (que `live` y `baseline` estén escuchando);
- desplaza las marcas de tiempo a `pylsl.local_clock()` con un `shift` fijo y empuja trozos cada 40 ms.

**Eventos, al ritmo de P03:**
- **Ancla:** el `STATE_ENTERED` de S1. Su marcador LSL (`mts_S1`) corresponde al `server_received_at` del mismo evento (`srv_S1`).
- Cada evento `e` se manda cuando `local_clock() = mts_S1 + shift + (srv_e − srv_S1)`, por `ws://127.0.0.1:8000/ws/session/<test>`, como `SESSION_EVENT`, en el orden de `id`. Se espera el `ACK` de cada uno.
- El `VALIDATION_EVENT` va como `VALIDATION_EVENT`, en su momento.
- Los payloads se mandan tal cual, con dos cambios:
  - el id de P03 se cambia por el de `TEST`;
  - los 20 `decision_id` se cambian por uuid nuevos, con el mismo mapa en `ADAPTATION_APPLIED` y `ADAPTATION_OUTCOME`, para no chocar con las filas de P03.
- `client_timestamp` se desplaza igual que lo demás.
- **No se mandan:** `EEG_BASELINE_RESULT`, porque `baseline.py` escribe el suyo.
- **Reloj del monitor:** justo antes de publicar, una sola `UPDATE experiment_sessions SET session_clock_started_at = …` sobre la fila `TEST`, para que el `session_elapsed_ms` de los payloads (los de P03) cuadre con el reloj del monitor. Toca solo esa fila.
- **Aborto:** si llega cualquier mensaje que no sea `ACK` ni `PONG` (un `DECISION` o un `ERROR`), o si el WebSocket se corta, el script para todo. Nunca se reconecta (ver SY2).
- Escribe un log en el scratchpad: el retraso de cada envío frente a su hora y cada respuesta.

**Prueba de humo, sin LSL ni base:**
- lee el XDF y los eventos;
- imprime cuántos eventos hay por tipo, la duración y el retraso esperado entre streams y eventos;
- cuadra los dos relojes, con el `STATE_ENTERED` de S7 del marcador frente al del evento (< 100 ms).

### SY1 · montaje (≈ 15 min) · 14:35–14:50 (después de C-1, §5)

1. **Conteos de antes**, en un archivo del scratchpad: `participants`, `experiment_sessions`, `session_events`, `eeg_sessions`, `eeg_epochs`, `eeg_trace_bins`, `adaptation_decisions`, `adaptation_applications`, `trials`, `trial_blocks`, `session_states`, `kanji_exposures`, `assemblies`, `assembly_attempts`, `hint_requests`, `distractor_interactions`, `peripheral_events`, `environment_applications`, `head_away_episodes`, `projection_errors`, `system_validation_events`, `session_config_snapshots`, `learner_profiles` y `kanji_substitutions`. Más `participants WHERE external_code LIKE 'TEST%'`, que tiene que dar 0.
2. **Interruptores para la prueba:**
   - `EEG_MONITOR_LIVE=true`, `MONITOR_LIVE_INDICES=true` y `MONITOR_INDICES_WINDOW=true` (si MI se integró);
   - `EEG_MONITOR_TRACES=true`, nuevo en `.env` (TR);
   - `EEG_LIVE_RULE=ica`;
   - `docker compose up -d backend` sin sesión y `printenv` en el contenedor.
   - `live.py` lee el mismo `.env` en la PC.
3. **Estado de la PC:** el software de AURA, Unity y LabRecorder cerrados, y ningún stream LSL en la PC (comprobación de 2 s).
4. **Participante `TEST2701`:**
   - `POST /participants`;
   - una `UPDATE` de `pretest_completed_at` en esa fila (`create_session` exige el pre-test);
   - `POST /sessions` con la condición de SY2, set C, visita 1 y la `config` de P03.
   - El backend manda a LabRecorder el nombre del archivo, pero LabRecorder está cerrado: falla en segundo plano sin efecto. Se anota.
5. **Procesos de la PC**, desde `backend\` y con `POSTGRES_HOST=127.0.0.1`: `python -m app.eeg.baseline <test>` y `live` dentro del proceso, como `run_live.py` de SIM5, para leer su CPU. Los dos esperan sus streams.
6. **El monitor** en `/monitor/<test>`:
   - en Firefox, en la segunda pantalla, para que Sebas lo vea;
   - en Playwright, para las medidas de C2b, a 1440 × 900.

**Parada SY1:** Sebas da la salida.

### SY2 · cómo se evita que el motor vuelva a decidir

**Recomendado: la sesión `TEST` es `STATIC`.**
- `_load_adaptation` ve que no es adaptativa y no carga el motor (`websocket.py:248-252`). Así no hay `state.feed`, ni `_eeg_source`, ni `EEG_STATUS` del backend.
- Las 20 decisiones de P03 entran como eventos guardados y proyectados, igual que cualquier evento. Nadie decide.
- **Lo que cambia:** la barra de arriba dice «Static» y no «Multimodal».
- **A favor:** P04 también es `STATIC`, así que se prueba el mismo camino del backend que tendrá esta noche.

**La otra opción (no la recomiendo):**
- se crea la sesión `STATIC`, el reproductor abre el WebSocket (sin motor), y después una `UPDATE` cambia la condición a `MULTIMODAL_ADAPTIVE`;
- el monitor diría «Multimodal»;
- **el riesgo:** si el WebSocket se reconecta, `_load_adaptation` reconstruye el motor y decide encima. El script no se reconecta nunca, pero un corte deja la prueba a medias.

**Comprobación, con cualquiera de las dos:**
- (a) **0 líneas `DECISION … session=<test>`** en `docker compose logs backend`: solo `_send_decision` las escribe, y las reproducidas no pasan por ahí;
- (b) **20 `ADAPTATION_DECISION`** en `TEST`, todas con uuid del mapa;
- (c) el reproductor no recibió ningún `DECISION`;
- (d) **0 `projection_errors`** de `TEST`.

**Si (d) falla** (que la proyección de una decisión necesite una sesión adaptativa): el panel de decisiones sale vacío, lo anoto, y la prueba sigue por lo demás. No se cambia de opción a mitad.

### SY3 · qué tablas toca

Toda la sesión `TEST` cuelga de `participants` con `ON DELETE CASCADE`. Lo comprobé en `pg_constraint`: `eeg_epochs` y `eeg_trace_bins` cuelgan de `eeg_sessions`, y esta de `experiment_sessions`.

| Quién escribe | Tablas |
| --- | --- |
| API | `participants`, `experiment_sessions`, `session_config_snapshots`, `eeg_sessions` (si `labrecorder_host` está puesto) |
| El WebSocket y `project_event` | `session_events`, `system_validation_events`, `session_states`, `trial_blocks`, `trials`, `kanji_exposures`, `assemblies`, `assembly_attempts`, `hint_requests`, `distractor_interactions`, `peripheral_events`, `environment_applications`, `head_away_episodes`, `adaptation_decisions`, `adaptation_applications`, y `projection_errors` si algo falla |
| Al llegar a S9 | `learner_profiles` (refresco del participante `TEST`) |
| `baseline.py` | `eeg_sessions` (alfa) y un `EEG_BASELINE_RESULT` |
| `live.py` | `eeg_epochs`, `eeg_sessions` (sincronía, referencia, ICA, latido, M1b, `traces_now`) y `eeg_trace_bins` |

**No toca:** las filas de P03 (solo se leen), el XDF de P03 (solo se lee), ni la carpeta de P03. Como no hay grabación, no se crea ningún XDF.

### SY4 · la corrida (≈ 16 min) · 14:50–15:06, con lo que se ve en cada panel

Lo que se espera, sacado de P03 (D-F6-315 (1)):

| Panel | Qué se tiene que ver |
| --- | --- |
| **Barra de arriba** | `TEST2701`, «Static», la etapa en curso y el reloj desde 00:00, avanzando como en P03 (S1 → S9 en 14,1 min) |
| **Signal quality (M1b)** | los 8 canales, con estado y RMS, actualizados cada 2,5 s desde la primera muestra |
| **Channel traces (TR)** | 8 carriles, 20 s, «Now» y «µV rms, 1 s»; en S3, las líneas «Tap 1–5» con el pulso de Cz cerca; ni hueco ni «No data for 12 s» mientras haya stream |
| **Sync** | 5/5 toques; un desfase cercano al de P03 (21,2 ms), con unos ms de diferencia porque la llegada de los trozos no es la misma |
| **Live indices (MI)** | «Indices from the end of S3» hasta el fin de S3. Después, la ventana de 20 s en ln con las líneas S4/S5/S6; «Fitting ICA» y luego «ICA applied at hh:mm:ss, r ≈ 0.83». En S7, solo S7 en z frente a S6, con los puntos de decisión. En S8–S9, otra vez la ventana, con «Raw, no decisions after S7» |
| **Decisions** | las 20 de P03: un cambio de ayuda (S7-005), y el EEG CONFIRMED 4, NEUTRAL 6 y UNAVAILABLE 10, tal como vienen en las decisiones reproducidas |
| **Events** | los eventos de P03 al ritmo de P03: `HEAD_AWAY` a 1,8 s con su triángulo, `STATE_ENTERED`, las respuestas, las decisiones |
| **System** | latido de menos de 3 s, alfa de S4 que da `baseline.py` (P03 dio 1,49–1,64), y sin hueco de EEG |
| **Fin** | S9 → `COMPLETED` → el aviso *Session ended* |

**Aviso:** las z del panel de índices salen de las épocas de esta corrida. Las de los puntos de decisión son las de P03, que vienen en el payload. Pueden diferir un poco, porque el corte en vivo no se repite igual entre pasadas (SIM5: 59 de 328 épocas). Se declara: no es un error del monitor.

**Lo que miro durante la corrida y anoto con la hora:** cualquier panel vacío, cualquier error en la consola del navegador, «No data», un reinicio del backend, y las líneas `live:` que imprima `live` (incluida «traces write failed»).

### SY5 · cómo mido C2b y C4 de TR

- **C2b, el tiempo de dibujo en el navegador (D-F6-297 (2)):**
  - En Playwright, a 1440 × 900 y luego a 1920 × 900, con `browser_evaluate` y sin tocar el código de la página:
    - un envoltorio de `window.fetch` para `/live/traces`: la hora en que llega la respuesta y la hora del `requestAnimationFrame` siguiente, después de que termina la tarea que dibuja. Eso es «llegada → cuadro pintado», una cota alta del dibujo;
    - un `PerformanceObserver('longtask')`, que cuenta las tareas de más de 50 ms.
  - Ventanas de medida: 2 min en S3 (toques) y 2 min en S7, a cada ancho, cambiando de ancho entre una y otra.
  - **Pasa si** el p95 < 50 ms y hay 0 tareas largas.
  - **Si no pasa,** la regla de TR5 dice bajar el refresco a 500 ms, no acortar la ventana. Eso es un cambio de código: no se hace hoy. Se lo digo a Sebas y queda como duda para PM. Mientras, TR sigue como diga D-F6-317 (1).
  - **Aviso:** es el Chromium de Playwright, no el navegador del operador. Se declara.
- **C4, la carga del monitor en la PC:**
  - Lo que esta prueba sí puede medir:
    - el CPU de `live` en la corrida, frente a SIM5 con M1b (20,5 s en 828 s);
    - el CPU del backend y de Postgres con `docker stats --no-stream` cada 30 s;
    - la edad de `traces_at` (debe quedar por debajo de 1 s);
    - el retraso de llegada de las épocas que devuelve `live` (mediana y máximo, frente a SIM5: 1,22 y 213,9 s);
    - 0 «traces write failed».
  - **La parte de `FRAME_HITCH` de C4 no se puede medir aquí.** Se queda en P04, con la regla de D-F6-314 (3) (D-F6-314 (5), D-F6-317 (1)).

### SY6 · borrar todo y contar (≈ 15 min) · 15:25–15:40

1. Parar el reproductor, `live` y `baseline`. Comprobar que no queda ningún stream LSL en la PC (2 s).
2. En una sola transacción:
   - `BEGIN`;
   - conteos de las tablas de SY1 que cuelgan de `TEST2701`;
   - `DELETE FROM participants WHERE external_code = 'TEST2701'`;
   - los conteos otra vez, que tienen que ser los de antes de SY1, y `LIKE 'TEST%'` = 0;
   - `COMMIT`, solo si cuadra. Si no, `ROLLBACK`, y se lo digo a Sebas.
3. **Archivos:**
   - `Pruebas_EEG\sub-TEST2701`, si existe (no debería, porque no hubo grabación);
   - los logs de la corrida en el scratchpad, después de sacar las cifras.
   - El XDF de P03 queda como estaba: se compara el tamaño y la fecha de antes y después.
4. Los conteos de antes y después van al borrador, como en SIM5.

### SY7 · tabla de resultados y margen · 15:40–16:00

- Cifras de C2b y C4 y lo que se vio en cada panel → borrador del 27 nov.
- **Parada SY:** Sebas mira el resultado y decide la vista de MI para P04 (D-F6-318 (3)).

**Tope a las 16:00.** Si a las 15:40 la corrida no terminó, se para donde esté, y se borra y se cuenta igual (SY6). Lo que no se midió se anota.

**Riesgos de la prueba:**
- **El ritmo de los eventos:** si `ACK` tarda, los envíos se van retrasando. El log da el retraso de cada uno, y un retraso de más de 1 s se anota.
- **Los dos relojes:** el ancla de S1 cuadra los streams y los eventos con menos de 100 ms de diferencia, que basta para lo que se ve en pantalla. La prueba de humo de SY0 lo comprueba antes.
- **La proyección de las decisiones en `STATIC`** (SY2 (d)).
- **El `VALIDATION_EVENT`:** si su payload depende del id de la sesión de otra forma, se rechaza. Se anota y no para la prueba.
- **Carga:** Playwright y Firefox abiertos al mismo tiempo pesan más que una visita. Se declara.

---

## 4 · Estado de la PC para P04 (17:30, `STATIC`) · D-F6-318 (3) · 16:00–17:00

**Interruptores para la visita**, puestos sin sesión en curso con `docker compose up -d backend` y comprobados con `printenv` en el contenedor y en `backend/.env` (que es lo que lee `live.py`):

| Interruptor | P04 | Por qué |
| --- | --- | --- |
| `EEG_MONITOR_LIVE` (M1b) | `true` | D-F6-314 (4) |
| `MONITOR_LIVE_INDICES` (MI) | `true` | D-F6-314 (4) |
| `MONITOR_INDICES_WINDOW` (MI fuera de S7) | `true` **solo si** se integró y se vio bien en la prueba; si no, `false`, y P04 ve la vista anterior | D-F6-318 (3) |
| `EEG_MONITOR_TRACES` (TR) | `true`, encendido por primera vez en una visita, con la regla de `FRAME_HITCH` de D-F6-314 (3): si pasa, sigue encendido; si no, se apaga después de P04 | D-F6-314 (5), D-F6-317 (1) |
| `EEG_LIVE_RULE` | `ica` | D-F6-289 (2) |

**Además:**
- PC en el commit integrado (o en `995f0aa` si no se integró nada), `git status` limpio y `/health/db` en 200. El commit va al README del export de P04.
- `dist` es el de la integración.
- No queda ningún stream, ningún reproductor ni ninguna fila `TEST`.
- **Kit de siempre** (D-F6-301 (2), D-F6-304 (4), D-F6-308 (1)–(2), D-F6-310 (2), D-F6-314 (7)):
  - Unity reabierto;
  - **LSL Stream Out como paso 1, antes de `preflight`**, con casilla en la hoja. Se lo pregunto a Sebas en voz alta antes de correr `preflight`. Con PF integrado, si se olvida, `preflight` da FAIL;
  - `preflight` sin FAIL;
  - ≈ 500 muestras en 2 s;
  - espuma de Fp1 antes del gel;
  - red apagada;
  - **molestia de 0 a 10 al terminar S5 y al final.** Se la pido en voz alta (D-F6-316 (2)).

**Qué pasa si algo no llega a tiempo:**

| Si… | Entonces… |
| --- | --- |
| PF no se integró | `preflight` sigue con el WARN. Sebas enciende LSL Stream Out primero y yo lo compruebo en voz alta (D-F6-315 (4)) |
| MI-P no se integró, o se integró pero no se vio bien | `MONITOR_INDICES_WINDOW=false`: P04 con la vista anterior de MI. La nueva entra con número |
| La integración falló y se deshizo | P04 con `995f0aa` tal cual: M1b y MI (vista anterior) encendidos, TR según D-F6-317 (1) |
| La prueba sintética no terminó o no se hizo | TR se enciende igual en P04, porque D-F6-317 (1) no depende de ella; la vista nueva de MI no (D-F6-318 (3)) |
| La prueba muestra que el monitor se cae con TR | Le propongo a Sebas apagar TR para P04 y dejo la duda escrita. No lo apago sin su OK, porque D-F6-317 (1) dice encenderlo |
| Llegan las 16:30 y la PC no está lista | Se para todo lo que no sea el kit. Ningún cambio de código ni de `.env` después de las 17:00 |

---

## 5 · Capturas de `/monitor` a todo el ancho para Diseño web (punto 6 de Sebas; D-F6-301 (6)) · ≈ 15 min en total

Diseño web espera la captura, según su Registro del 26 nov a las 20:05. Ese Registro no está en el espejo, así que no lo pude leer. Revisa la pantalla a todo el ancho, como dejaba pendiente W.

**La segunda pantalla** es `DISPLAY5`, de **1920 × 1080**, a la izquierda de la principal (que es de 1707 × 1067 con escala). Lo leí con `Screen.AllScreens` a las 11:50.

**Cómo se hace:**
- **Con Playwright,** con una ventana de 1920 × 1080: es la resolución de esa pantalla, y así la captura se puede repetir. Una captura de Firefox con F11 en `DISPLAY5` también sirve, pero saca la barra del navegador si no está en pantalla completa.
- **Sobre el `dist` integrado** (después de IN), no sobre el servidor de desarrollo, para que sea la página que ve la visita.
- **El monitor sigue a 900 px de alto** (`h-[900px]`, W). A 1080 queda una franja de 180 px abajo. Es lo que hay hoy y Diseño web lo tiene que ver, así que no se recorta.
- **Solo en claro.** La oscura, si sobra tiempo.
- Las capturas son archivos nuevos en `Claude outputs/design-handoff/monitor/`. No toco ningún archivo de Diseño web (§3 del tablero).

**Las dos capturas:**

| Captura | Cuándo | Qué datos | Nombre |
| --- | --- | --- | --- |
| **C-1 · obligatoria hoy** | **14:30–14:35**, justo después de IN, antes de SY1 | la fixture del checkpoint del monitor que ya existe (datos inventados, ningún participante), con S7 en curso. Los interruptores quedan como en la visita | `Monitor_en_vivo_1920x1080_claro.png` |
| **C-2 · si se puede** | En SY4, en la ventana de 2 min en S7 a 1920 px de SY5 (≈ 15:00) | la sesión `TEST2701` con la prueba sintética corriendo: M1b, MI y TR encendidos | `Monitor_en_vivo_1920x1080_prueba_sintetica_claro.png` |

- **C-2 enseña datos de P03 bajo el código `TEST2701`:** decisiones, z y trazas. P03 es un código, no un nombre (D-F6-192), y la captura no sale de la PC.
- **C-2 no necesita otra corrida:** se saca con el mismo Playwright de C2b. La captura se hace justo después de cerrar la ventana de medida, para que no la ensucie.

**Hecho cuando:**
- C-1 está en `design-handoff/monitor/`, mide 1920 × 1080, no tiene franja vacía a la derecha ni scroll, y los paneles salen en el orden del dibujo;
- C-2 está ahí también, o la razón de que no esté va en el borrador;
- hay una línea en el borrador para Diseño web, con los nombres y la resolución.

**Puntos de corte:**
- Si IN no se integró, C-1 se saca igual a las 14:30, sobre el `dist` de `995f0aa`, que ya tiene W. Lo declaro en el nombre: `…_995f0aa_claro.png`.
- Si la prueba sintética no llega a S7 antes de las 15:40, no hay C-2.
- Nada de esto pasa de las 16:00.

**Riesgo:** con Playwright y Firefox abiertos durante SY4, la captura no cambia nada del monitor. La carga sí se declara en C4 (SY5).

---

## Casillas de hoy

- [x] 0 · OK de Sebas (D-F6-320), textos §7.6, condición de `TEST`, subagente para SY0
- [x] SY0 · reproductor y prueba de humo (scratchpad)
- [x] MI-B · (`947212b`, pytest 576) backend, interruptor `MONITOR_INDICES_WINDOW`, pytest · commit · parada
- [x] PF · (`ae803bd`) FAIL de `preflight` sin AURA, su test · commit · parada
- [x] MI-P · (`8dd051c`, Vitest 172) página, Vitest, capturas a 1440 y a 1920 · commit · parada
- [x] RV · (`73952fd`) //review del diff y arreglos
- [x] IN · (`8a2df2a`, 12:17–12:21) `pg_dump`, integración, pytest y Vitest, `dist`, `up -d`, `printenv` · antes de las 14:30
- [x] C-1 · (12:22) captura de `/monitor` a 1920 × 1080 con la fixture → `design-handoff/monitor/` · 14:30–14:35
- [x] SY1 · conteos de antes, interruptores, `TEST2701`, `baseline` y `live`, monitor
- [x] SY4 · (12:24:30–12:38:57) corrida de 14,1 min con los paneles anotados
- [x] SY2 · comprobación de que nadie decidió: (a)–(d)
- [x] SY5 · C2b a 1440 y a 1920; C4 sin `FRAME_HITCH`
- [x] C-2 · captura a 1920 × 1080 con la prueba sintética en S7 (si se puede)
- [x] SY6 · (12:46) borrar en una transacción, contar antes y después, archivos · antes de las 16:00
- [ ] P04 · interruptores, `printenv`, `git status`, kit · antes de las 17:00

**No entra en este plan:**
- bajar el refresco de TR a 500 ms (solo si C2b falla, y con número);
- el A-7 «n/a» de `verify_eeg.sql`, los 5 tests que leen el `.env` real y el salto de un bin (después del piloto, D-F6-314 (9));
- cualquier cambio de regla o de umbral. El análisis de sensibilidad de D-F6-318 (4) es del chat de EEG, en papel.
