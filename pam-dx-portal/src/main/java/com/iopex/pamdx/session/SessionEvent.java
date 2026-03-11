package com.iopex.pamdx.session;

/**
 * Event pushed via SSE to the demo page.
 * type values: SESSION_STARTED | CREDENTIAL_INJECTED | ROTATION_STARTING |
 *              ROTATION_PROGRESS | ROTATION_COMPLETE | SESSION_ENDED | ERROR
 */
public record SessionEvent(
    String type,
    String message,
    int progressPct,    // 0-100, used for ROTATION_PROGRESS events
    Object data         // optional structured payload (SessionRecord snapshot, etc.)
) {
    /** Convenience constructor for events without progress or data. */
    public SessionEvent(String type, String message) {
        this(type, message, 0, null);
    }
}
