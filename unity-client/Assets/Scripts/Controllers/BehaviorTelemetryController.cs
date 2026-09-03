using System.Collections.Generic;
using NeuroAdaptiveVR.Networking;
using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Responsabilidad (spec seccion 14): punto unico de emision de
    /// eventos de trial/hint/answer/distractor/interaccion (vocabulario
    /// completo en spec 11.1: TRIAL_STARTED, ANSWER_SELECTED,
    /// HEAD_AWAY, etc.) hacia SessionCommunicationClient.
    ///
    /// FASE 1: implementa el wrapper generico (Emit) que ya usa el
    /// walking skeleton para SESSION_EVENT. El vocabulario de eventos
    /// conductuales completo se instrumenta en Fase 3 (M2 apunta a
    /// "Behavior-Instrumented VR Prototype").
    ///
    /// NOTA (28 ago 2026): el payload paso de ser un string con JSON
    /// serializado a un Dictionary. El backend espera un OBJETO bajo la
    /// llave "payload" (ver backend/app/api/routes/websocket.py); mandar
    /// un string dejaba el payload vacio en la base sin dar error.
    /// </summary>
    [RequireComponent(typeof(SessionCommunicationClient))]
    public class BehaviorTelemetryController : MonoBehaviour
    {
        [SerializeField] private SessionCommunicationClient communicationClient;

        private void Awake()
        {
            if (communicationClient == null)
                communicationClient = GetComponent<SessionCommunicationClient>();
        }

        public void Emit(string eventType, Dictionary<string, object> payload = null)
        {
            communicationClient.SendSessionEvent(eventType, payload);
        }

        /// <summary>
        /// Atajo para el caso mas comun: un evento con un solo par
        /// clave/valor. Equivale a Emit(eventType, new Dictionary...).
        /// </summary>
        public void Emit(string eventType, string key, object value)
        {
            communicationClient.SendSessionEvent(eventType, new Dictionary<string, object>
            {
                { key, value },
            });
        }
    }
}
