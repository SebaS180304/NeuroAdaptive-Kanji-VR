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

        public void Emit(string eventType, string payloadJson = "{}")
        {
            communicationClient.SendSessionEvent(eventType, payloadJson);
        }
    }
}
