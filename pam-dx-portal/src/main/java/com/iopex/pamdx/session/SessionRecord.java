package com.iopex.pamdx.session;

import java.time.Instant;

/**
 * Immutable snapshot of a privileged session.
 * maskedSecret shows only the first 4 and last 4 chars — never the full credential.
 */
public record SessionRecord(
    String sessionId,
    String userId,
    String accountId,
    String accountName,
    String maskedSecret,        // "P@ss••••••••••••word" — displayed in UI
    Instant startedAt,
    Instant endedAt,            // null while ACTIVE
    SessionStatus status,
    boolean rotationTriggered,
    String rotationNewMasked    // masked form of new credential after rotation, or null
) {
    /** Mask a raw credential: show first 4 + "••••••••••••" + last 4. */
    public static String mask(String raw) {
        if (raw == null || raw.length() < 10) return "••••••••••••";
        return raw.substring(0, 4) + "••••••••••••" + raw.substring(raw.length() - 4);
    }
}
