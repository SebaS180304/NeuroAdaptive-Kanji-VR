using System;
using System.Collections.Generic;
using System.Text;
using Newtonsoft.Json;
using NeuroAdaptiveVR.Core;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Networking;

namespace NeuroAdaptiveVR.EditorTools
{
    /// <summary>
    /// Crea una sesion por REST y deja el SessionBootstrap de la escena apuntando
    /// a ella.
    ///
    /// POR QUE EXISTE
    /// --------------
    /// Desde Fase 2 la sesion la crea el investigador y Unity la consume (spec
    /// 7.1). El procedimiento manual son dos POST encadenados --el segundo
    /// necesita el id que devuelve el primero-- mas copiar un UUID al Inspector.
    /// Copiar un UUID a mano tres veces al dia acaba, antes o despues, en una
    /// corrida apuntando a la sesion de ayer. Y una corrida apuntando a la sesion
    /// equivocada produce datos que parecen validos.
    ///
    /// Esto NO reemplaza al Research Dashboard (Fase 7). Es el andamio mientras
    /// tanto, y hace exactamente lo mismo que haria a mano.
    /// </summary>
    public static class SessionSetupTool
    {
        private const string Log = "[SessionSetup]";

        [MenuItem("Tools/NeuroAdaptive VR/Crear sesion y cablearla (set A, seed del dia)", priority = 120)]
        public static void CreateDefault()
        {
            CreateAndWire("http://localhost:8000", "A",
                          DateTime.Now.ToString("yyyyMMdd"), "STATIC", 1);
        }

        /// <summary>
        /// Crea participante y sesion, y escribe el id en el SessionBootstrap de
        /// la escena abierta. Devuelve el session_id, o null si algo fallo.
        /// </summary>
        public static string CreateAndWire(string backendUrl, string kanjiSet, string seed,
                                           string condition, int visitNumber)
        {
            string participantId = PostJson($"{backendUrl}/participants",
                new Dictionary<string, object>
                {
                    { "external_code", $"TEST_F2_{DateTime.Now:yyyyMMdd_HHmmss}" },
                    { "consent_obtained", true },
                });

            if (participantId == null) return null;
            string pid = Field(participantId, "id");
            Debug.Log($"{Log} Participante {pid}");

            string sessionBody = PostJson($"{backendUrl}/sessions",
                new Dictionary<string, object>
                {
                    { "participant_id", pid },
                    { "condition", condition },
                    { "assigned_kanji_set", kanjiSet },
                    { "random_seed", seed },          // el backend lo guarda como texto
                    { "visit_number", visitNumber },
                    { "software_version", "fase2-pruebas" },
                });

            if (sessionBody == null) return null;
            string sid = Field(sessionBody, "id");

            Debug.Log($"{Log} Sesion {sid} · set {kanjiSet} · seed \"{seed}\" -> " +
                      $"{StableHash.Of(seed)} · {condition} · visita {visitNumber} · " +
                      $"clock {Field(sessionBody, "session_clock_started_at")}");

            if (!Wire(backendUrl, sid)) return sid;
            return sid;
        }

        /// <summary>
        /// Escribe el id en el SessionBootstrap y apaga createNewSessionOnPlay.
        /// Los dos a la vez: dejar el id puesto con el flag encendido crearia una
        /// sesion nueva igualmente y el id serviria de decoracion.
        /// </summary>
        private static bool Wire(string backendUrl, string sessionId)
        {
            var bootstrap = UnityEngine.Object.FindAnyObjectByType<SessionBootstrap>();
            if (bootstrap == null)
            {
                Debug.LogError($"{Log} No hay SessionBootstrap en la escena abierta. " +
                               $"La sesion {sessionId} existe, pero hay que pegar el id a mano.");
                return false;
            }

            var so = new SerializedObject(bootstrap);
            so.FindProperty("backendHttpUrl").stringValue = backendUrl;
            so.FindProperty("createNewSessionOnPlay").boolValue = false;
            so.FindProperty("existingSessionId").stringValue = sessionId;
            so.ApplyModifiedPropertiesWithoutUndo();

            EditorUtility.SetDirty(bootstrap);
            var scene = EditorSceneManager.GetActiveScene();
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);

            Debug.Log($"{Log} SessionBootstrap cableado y escena guardada. " +
                      "createNewSessionOnPlay queda apagado.");
            return true;
        }

        /// <summary>
        /// Vuelca el estado de una sesion sin pasar por psql. Sirve para
        /// comprobar de un vistazo que current_state y status siguen a la sesion
        /// -- los dos se quedaban quietos hasta el 16 de septiembre.
        /// </summary>
        public static void ReportSession(string backendUrl, string sessionId)
        {
            using var req = UnityWebRequest.Get($"{backendUrl}/sessions/{sessionId}");
            req.timeout = 10;
            var op = req.SendWebRequest();
            while (!op.isDone) { }

            if (req.result != UnityWebRequest.Result.Success)
            {
                Debug.LogError($"{Log} GET sesion fallo: {req.error}");
                return;
            }

            string body = req.downloadHandler.text;
            Debug.Log($"{Log} {sessionId}\n" +
                      $"  current_state      = {Field(body, "current_state")}\n" +
                      $"  status             = {Field(body, "status")}\n" +
                      $"  assigned_kanji_set = {Field(body, "assigned_kanji_set")}\n" +
                      $"  random_seed        = {Field(body, "random_seed")}\n" +
                      $"  condition          = {Field(body, "condition")}\n" +
                      $"  visit_number       = {Field(body, "visit_number")}");
        }

        // ------------------------------------------------------------------

        /// <summary>
        /// POST sincrono. En un script de Editor no hay corrutina donde ceder, y
        /// el timeout evita que una espera activa cuelgue el Editor si el backend
        /// no esta levantado.
        /// </summary>
        private static string PostJson(string url, Dictionary<string, object> body)
        {
            string json = JsonConvert.SerializeObject(body);

            using var req = new UnityWebRequest(url, UnityWebRequest.kHttpVerbPOST);
            req.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(json));
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json");
            req.timeout = 10;

            var op = req.SendWebRequest();
            while (!op.isDone) { }

            if (req.result != UnityWebRequest.Result.Success)
            {
                Debug.LogError($"{Log} POST {url} fallo: {req.error} · " +
                               $"{req.downloadHandler?.text}\n" +
                               "Si es error de conexion, el backend no esta arriba: " +
                               "docker compose up -d db backend");
                return null;
            }

            return req.downloadHandler.text;
        }

        private static readonly JsonSerializerSettings Raw = new()
        {
            // Misma razon que en SessionBootstrap: sin esto Newtonsoft convierte
            // el timestamp ISO en DateTime y lo devuelve con formato local.
            DateParseHandling = DateParseHandling.None,
        };

        private static string Field(string json, string key)
        {
            var parsed = JsonConvert.DeserializeObject<Dictionary<string, object>>(json, Raw);
            return parsed != null && parsed.TryGetValue(key, out var v) ? v?.ToString() : null;
        }
    }
}
