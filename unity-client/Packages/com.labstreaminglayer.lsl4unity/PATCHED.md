# LSL4Unity, embedded with one patch

Upstream: https://github.com/labstreaminglayer/LSL4Unity at `75d54ab160edaf02d2173350bbd91f1afbdb66d8`
(master, 31 Jul 2023, the latest). Embedded on 2 Nov 2026 for the F4 marker stream (D-F6-74, D-F6-132).

The only change: `Runtime/Scripts/BaseOutlet.cs` line 48, `gameObject.GetInstanceID()` →
`gameObject.GetEntityId().ToString()`. In this Unity version `Object.GetInstanceID()` is obsolete
as an error (CS0619), so the upstream package does not compile. The project does not use
BaseOutlet; it only needs `Runtime/LSL.cs` and the liblsl binaries in `Plugins/`.

To update: copy a newer upstream commit over this folder and re-apply the patch if still needed.
