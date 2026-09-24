using System.Collections.Generic;
using NeuroAdaptiveVR.Controllers;
using NeuroAdaptiveVR.Data;
using Unity.XR.CoreUtils;
using UnityEngine;
using UnityEngine.InputSystem;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// Puts the participant's view back at the designed eye pose: eye at
    /// 1.36 m, looking straight at the Learning Board (Diseno_Sala_ESL.md,
    /// "participant position: origin, facing +Z").
    ///
    /// WHY IT EXISTS (24 September, first full S1-S9 pass)
    /// ---------------------------------------------------
    /// After moving around, there was no way back to the pose where the room
    /// reads as designed. That is a comfort problem and, underneath, a
    /// measurement one: every ESL prop angle was placed relative to that pose,
    /// so a participant who drifted half a metre sideways sees a different
    /// peripheral layer than the one the condition specifies.
    ///
    /// HOW IT IS TRIGGERED
    /// -------------------
    /// - Left controller Menu button (≡). The only Quest button left free for
    ///   apps, and never used to answer, so it cannot fire by accident while
    ///   choosing a card. A button on the board would be useless: whoever is
    ///   lost cannot see the board.
    /// - R on the keyboard, for the Editor and for the researcher.
    /// - Automatically when the session starts (SessionFlowRunner, S1), so every
    ///   participant begins from the same pose regardless of how the headset
    ///   was put on (spec 7.2, "participant appears at the central station").
    ///
    /// Every recenter emits VIEW_RECENTERED with the pose it corrected.
    /// </summary>
    public class ViewRecenter : MonoBehaviour
    {
        private const string Log = "[ViewRecenter]";

        [SerializeField] private XROrigin origin;
        [SerializeField] private BehaviorTelemetryController telemetry;

        [Tooltip("Designed eye position in world space (Diseno_Sala_ESL.md: origin, eye at 1.36 m).")]
        [SerializeField] private Vector3 designEyePosition = new(0f, 1.36f, 0f);

        [Tooltip("Designed facing, in degrees of world yaw. 0 = +Z, towards the Learning Board.")]
        [SerializeField] private float designYaw = 0f;

        [Tooltip("Ignore a second press within this window, so one press is one event.")]
        [SerializeField] private float cooldownSeconds = 0.5f;

        private InputAction _action;
        private float _lastRecenter = -999f;

        private void Awake()
        {
            if (origin == null) origin = FindAnyObjectByType<XROrigin>();
            if (telemetry == null) telemetry = FindAnyObjectByType<BehaviorTelemetryController>();

            _action = new InputAction("Recenter view", InputActionType.Button);
            // Usage-based path, not a device-specific one: it resolves to the
            // Menu button on Oculus Touch and on any other profile that exposes it.
            _action.AddBinding("<XRController>{LeftHand}/{MenuButton}");
            _action.AddBinding("<Keyboard>/r");
        }

        private void OnEnable()
        {
            _action.performed += OnPressed;
            _action.Enable();
        }

        private void OnDisable()
        {
            _action.performed -= OnPressed;
            _action.Disable();
        }

        private void OnDestroy() => _action?.Dispose();

        private void OnPressed(InputAction.CallbackContext ctx)
        {
            string source = ctx.control?.device is Keyboard ? "KEYBOARD" : "LEFT_MENU_BUTTON";
            Recenter(source);
        }

        /// <param name="reason">Why: LEFT_MENU_BUTTON, KEYBOARD, SESSION_START, ...</param>
        public void Recenter(string reason)
        {
            if (Time.realtimeSinceStartup - _lastRecenter < cooldownSeconds) return;
            if (origin == null || origin.Camera == null)
            {
                Debug.LogWarning($"{Log} No XROrigin/camera; cannot recenter.");
                return;
            }
            _lastRecenter = Time.realtimeSinceStartup;

            var cam = origin.Camera.transform;
            Vector3 posBefore = cam.position;
            float yawBefore = cam.eulerAngles.y;

            // Rotate first, then translate. Rotating around the camera keeps
            // the camera where it is; doing it the other way round would move
            // the camera off the target it was just placed on.
            float yawError = Mathf.DeltaAngle(designYaw, yawBefore);
            origin.RotateAroundCameraUsingOriginUp(-yawError);
            origin.MoveCameraToWorldLocation(designEyePosition);

            float moved = Vector3.Distance(posBefore, cam.position);
            Debug.Log($"{Log} {reason} · yaw error {yawError:0.0}° · moved {moved:0.00} m " +
                      $"· camera now {cam.position:F2}");

            telemetry?.Emit(TelemetryEvents.ViewRecentered, new Dictionary<string, object>
            {
                { "reason", reason },
                { "yaw_error_deg", Mathf.Round(yawError * 10f) / 10f },
                { "offset_m", Mathf.Round(moved * 1000f) / 1000f },
                { "camera_before", new[] { posBefore.x, posBefore.y, posBefore.z } },
            });
        }
    }
}
