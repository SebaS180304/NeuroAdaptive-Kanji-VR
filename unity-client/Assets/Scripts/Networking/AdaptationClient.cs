using System;
using System.Collections.Generic;
using NeuroAdaptiveVR.Data;
using UnityEngine;

namespace NeuroAdaptiveVR.Networking
{
    /// <summary>
    /// F5a (Planteamiento_Tecnico_F5a.md §8.2): listens for the backend's
    /// DECISION messages and keeps the last one per trial_id. It applies
    /// nothing: SessionFlowRunner takes the decision of the trial that just
    /// closed, between trials, and the controllers' own guards still apply.
    ///
    /// A decision that arrives after its trial was skipped (TIMEOUT) is
    /// discarded and logged, never applied late (D1, criterion 12).
    /// </summary>
    public class AdaptationClient : MonoBehaviour
    {
        [SerializeField] private SessionCommunicationClient client;

        private readonly Dictionary<string, IncomingMessage> _byTrial = new();
        private readonly HashSet<string> _skipped = new();

        public event Action<IncomingMessage> OnDecision;

        public int LateDiscarded { get; private set; }

        private void Awake()
        {
            if (client == null) client = GetComponent<SessionCommunicationClient>();
            if (client == null) client = FindAnyObjectByType<SessionCommunicationClient>();
        }

        private void OnEnable() { if (client != null) client.OnMessageReceived += Accept; }
        private void OnDisable() { if (client != null) client.OnMessageReceived -= Accept; }

        /// <summary>Entry point for every incoming message; public so the harness can feed it.</summary>
        public void Accept(IncomingMessage message)
        {
            if (message == null || message.Type != "DECISION" || string.IsNullOrEmpty(message.TrialId)) return;

            if (_skipped.Contains(message.TrialId))
            {
                LateDiscarded++;
                Debug.LogWarning($"[AdaptationClient] DECISION {message.DecisionId} for {message.TrialId} arrived " +
                                 "after the trial was skipped (TIMEOUT). Discarded, not applied late.");
                return;
            }
            _byTrial[message.TrialId] = message;
            Debug.Log($"[AdaptationClient] {message.TrialId}: {message.Action} {message.Dimension} " +
                      $"{message.FromLevel}->{message.ToLevel} ({message.ReasonCode}) {message.Explanation}");
            OnDecision?.Invoke(message);
        }

        /// <summary>The decision of this trial, once; false if it has not arrived.</summary>
        public bool TryTake(string trialId, out IncomingMessage decision)
        {
            if (trialId != null && _byTrial.TryGetValue(trialId, out decision))
            {
                _byTrial.Remove(trialId);
                return true;
            }
            decision = null;
            return false;
        }

        /// <summary>The trial was closed without its decision: anything that arrives later is discarded.</summary>
        public void MarkSkipped(string trialId)
        {
            if (trialId != null) _skipped.Add(trialId);
        }

        /// <summary>Forget everything, at the start of a block.</summary>
        public void Clear()
        {
            _byTrial.Clear();
            _skipped.Clear();
        }
    }

    /// <summary>
    /// What to do with the decision of the trial that just closed. Pure, so
    /// the harness checks every branch without a scene (A1–A5).
    /// </summary>
    public static class AdaptationApply
    {
        public const string NoChange = "NO_CHANGE";
        public const string ChangeEnvironment = "CHANGE_ENVIRONMENT";
        public const string ChangeAssistance = "CHANGE_ASSISTANCE";

        // ADAPTATION_SKIPPED reasons (§8.3)
        public const string ReasonTimeout = "TIMEOUT";
        public const string ReasonGuard = "GUARD";
        public const string ReasonNotAllowed = "NOT_ALLOWED";
        public const string ReasonInvalid = "INVALID";

        public enum Outcome
        {
            /// <summary>Not an adaptive S7: nothing is waited for, nothing is emitted.</summary>
            NotApplicable,
            /// <summary>NO_CHANGE arrived: the backend already recorded it.</summary>
            Nothing,
            Apply,
            SkipTimeout,
            SkipGuard,
            SkipNotAllowed,
            SkipInvalid,
        }

        public static Outcome Resolve(bool adaptationAllowed, bool trialInProgress, IncomingMessage decision,
                                      bool hasNextTrial, out bool isEsl, out StimulationOrAssistanceLevel to)
        {
            isEsl = false;
            to = StimulationOrAssistanceLevel.Off;

            if (!adaptationAllowed) return Outcome.NotApplicable;
            if (decision == null) return Outcome.SkipTimeout;
            if (decision.Action == NoChange) return Outcome.Nothing;
            if (!hasNextTrial) return Outcome.SkipNotAllowed;   // nothing left to apply it to

            bool esl = decision.Action == ChangeEnvironment && decision.Dimension == "ESL";
            bool lal = decision.Action == ChangeAssistance && decision.Dimension == "LAL";
            if ((!esl && !lal)
                || !EnumWire<StimulationOrAssistanceLevel>.TryParse(decision.ToLevel, out to)
                || (to != StimulationOrAssistanceLevel.Low && to != StimulationOrAssistanceLevel.Medium
                    && to != StimulationOrAssistanceLevel.High))
                return Outcome.SkipInvalid;

            isEsl = esl;
            return trialInProgress ? Outcome.SkipGuard : Outcome.Apply;
        }

        public static string ReasonOf(Outcome outcome) => outcome switch
        {
            Outcome.SkipTimeout => ReasonTimeout,
            Outcome.SkipGuard => ReasonGuard,
            Outcome.SkipNotAllowed => ReasonNotAllowed,
            Outcome.SkipInvalid => ReasonInvalid,
            _ => null,
        };
    }
}
