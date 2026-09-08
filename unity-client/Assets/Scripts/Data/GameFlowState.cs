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
    /// CORRECCION (7 sep 2026, paso 0 de Fase 2): hasta entonces
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

    public static class GameFlowStateExtensions
    {
        /// <summary>
        /// String que el backend espera para este estado. Es lo que se manda
        /// en el payload de STATE_ENTERED y en PATCH /sessions/{id}/state.
        /// </summary>
        public static string ToWireValue(this GameFlowState state)
            => EnumWire<GameFlowState>.Value(state);

        /// <summary>Inverso, para mensajes que vengan del backend.</summary>
        public static bool TryFromWireValue(string wireValue, out GameFlowState state)
            => EnumWire<GameFlowState>.TryParse(wireValue, out state);

        /// <summary>
        /// Prefijo corto del estado para componer identificadores legibles
        /// (`trial_id` = "S7-007", ver database/EVENT_CONTRACT.md seccion 4.1).
        /// Es la parte anterior al primer guion bajo del nombre del miembro:
        /// S0..S10.
        /// </summary>
        public static string ShortCode(this GameFlowState state)
        {
            string name = state.ToString();
            int underscore = name.IndexOf('_');
            return underscore > 0 ? name.Substring(0, underscore) : name;
        }
    }
}
