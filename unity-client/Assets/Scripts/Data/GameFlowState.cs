namespace NeuroAdaptiveVR.Data
{
    /// <summary>
    /// Estados formales S0-S10 del Game Flow v1 (spec seccion 7).
    /// Debe reflejar exactamente el enum `GameFlowState` del backend
    /// (backend/app/models/session.py) -- los nombres viajan como
    /// strings en los mensajes WebSocket.
    /// </summary>
    public enum GameFlowState
    {
        S0_SessionInitialization,
        S1_WelcomeOrientation,
        S2_VRTutorial,
        S3_SystemValidation,
        S4_EEGBaseline,
        S5_StandardizedLearning,
        S6_GuidedPracticeCalibration,
        S7_ExperimentalRetrieval,
        S8_ImmediateAssessment,
        S9_SessionSummary,
        S10_HCISelfReport,
    }
}
