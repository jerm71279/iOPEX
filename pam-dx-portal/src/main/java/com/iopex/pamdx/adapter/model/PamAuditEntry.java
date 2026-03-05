package com.iopex.pamdx.adapter.model;

import java.time.Instant;
import java.util.Map;

/**
 * Normalized PAM audit log entry — vendor-agnostic representation.
 */
public record PamAuditEntry(
    String entryId,
    Instant timestamp,
    String action,
    String user,
    String target,
    String containerName,
    String result,
    Map<String, Object> details
) {
    public PamAuditEntry {
        if (details == null) details = Map.of();
    }
}
