using System;
using System.Collections.Generic;
using System.Reflection;
using System.Runtime.Serialization;

namespace NeuroAdaptiveVR.Data
{
    /// <summary>
    /// Estados formales S0-S10 del Game Flow v1 (spec seccion 7).
    ///
    /// El nombre del miembro sigue la convencion de C#; el string que viaja
    /// por el WebSocket es el de <see cref="EnumMemberAttribute"/>, y ese si
    /// tiene que coincidir EXACTAMENTE con el enum `GameFlowState` del
    /// backend (backend/app/models/session.py) y con el tipo
    /// `game_flow_state` de PostgreSQL.
    ///
    /// CORRECCION (7 sep 2026, paso 0 de Fase 2): hasta hoy
    /// GameFlowController serializaba con `.ToString()`, que devuelve el
    /// nombre del miembro -- "S1_WelcomeOrientation" en vez de
    /// "S1_WELCOME_ORIENTATION". El docstring de este archivo ya afirmaba
    /// que los dos enums coincidian, y no coincidian. No fallaba porque
    /// `session_events.payload` es JSONB libre y acepta cualquier string,
    /// pero rompia en dos lugares en cuanto se usara de verdad: un
    /// `PATCH /sessions/{id}/state` con el nombre del miembro devuelve 422
    /// (Pydantic valida por valor), y `payload->>'state'` no castea al enum
    /// de PostgreSQL.
    ///
    /// Usa siempre <see cref="GameFlowStateExtensions.ToWireValue"/> para
    /// mandar un estado al backend. Nunca `.ToString()`.
    /// </summary>
    public enum GameFlowState
    {
        [EnumMember(Value = "S0_SESSION_INITIALIZATION")]
        S0_SessionInitialization,

        [EnumMember(Value = "S1_WELCOME_ORIENTATION")]
        S1_WelcomeOrientation,

        [EnumMember(Value = "S2_VR_TUTORIAL")]
        S2_VRTutorial,

        [EnumMember(Value = "S3_SYSTEM_VALIDATION")]
        S3_SystemValidation,

        [EnumMember(Value = "S4_EEG_BASELINE")]
        S4_EEGBaseline,

        [EnumMember(Value = "S5_STANDARDIZED_LEARNING")]
        S5_StandardizedLearning,

        [EnumMember(Value = "S6_GUIDED_PRACTICE_CALIBRATION")]
        S6_GuidedPracticeCalibration,

        [EnumMember(Value = "S7_EXPERIMENTAL_RETRIEVAL")]
        S7_ExperimentalRetrieval,

        [EnumMember(Value = "S8_IMMEDIATE_ASSESSMENT")]
        S8_ImmediateAssessment,

        [EnumMember(Value = "S9_SESSION_SUMMARY")]
        S9_SessionSummary,

        [EnumMember(Value = "S10_HCI_SELF_REPORT")]
        S10_HCISelfReport,
    }

    /// <summary>
    /// Traduccion entre los miembros del enum y los strings que viajan por
    /// el protocolo. El atributo de cada miembro es la unica fuente de
    /// verdad: no hay una segunda lista que se pueda desincronizar.
    /// </summary>
    public static class GameFlowStateExtensions
    {
        private static readonly Dictionary<GameFlowState, string> ToWire = BuildToWire();
        private static readonly Dictionary<string, GameFlowState> FromWire = BuildFromWire();

        /// <summary>
        /// String que el backend espera para este estado. Es lo que se manda
        /// en el payload de STATE_ENTERED y en PATCH /sessions/{id}/state.
        /// </summary>
        public static string ToWireValue(this GameFlowState state) => ToWire[state];

        /// <summary>
        /// Inverso de <see cref="ToWireValue"/>, para mensajes que vengan del
        /// backend. Devuelve false si el string no corresponde a ningun
        /// estado conocido, en vez de lanzar: un backend mas nuevo que este
        /// cliente no deberia tumbar la sesion.
        /// </summary>
        public static bool TryFromWireValue(string wireValue, out GameFlowState state)
        {
            if (wireValue != null && FromWire.TryGetValue(wireValue, out state)) return true;
            state = default;
            return false;
        }

        private static Dictionary<GameFlowState, string> BuildToWire()
        {
            var map = new Dictionary<GameFlowState, string>();
            var type = typeof(GameFlowState);

            foreach (GameFlowState state in Enum.GetValues(type))
            {
                var field = type.GetField(state.ToString());
                var attribute = field?.GetCustomAttribute<EnumMemberAttribute>();

                // Fallo ruidoso y temprano, a proposito. Si el atributo falta
                // -- porque se agrego un estado sin el, o porque el stripping
                // de IL2CPP lo elimino en un build -- lo que queremos es una
                // excepcion en el primer uso, no que la sesion entera mande
                // silenciosamente strings que el backend rechaza. Ese fue
                // exactamente el modo de falla del bug de payload_json.
                if (attribute == null || string.IsNullOrEmpty(attribute.Value))
                {
                    throw new InvalidOperationException(
                        $"GameFlowState.{state} no tiene [EnumMember(Value = ...)]. " +
                        "Cada estado necesita su valor de cable explicito para " +
                        "coincidir con el enum game_flow_state del backend.");
                }

                map[state] = attribute.Value;
            }

            return map;
        }

        private static Dictionary<string, GameFlowState> BuildFromWire()
        {
            var map = new Dictionary<string, GameFlowState>();
            foreach (var pair in ToWire) map[pair.Value] = pair.Key;
            return map;
        }
    }
}
