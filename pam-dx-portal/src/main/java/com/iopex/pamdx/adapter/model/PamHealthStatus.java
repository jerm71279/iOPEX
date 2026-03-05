package com.iopex.pamdx.adapter.model;

import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * Health/preflight check result from a PAM vendor adapter.
 */
public record PamHealthStatus(
    String vendor,
    boolean connected,
    String version,
    Instant checkedAt,
    List<CheckItem> checks
) {
    public record CheckItem(String name, boolean passed, String message) {}

    public PamHealthStatus {
        if (checkedAt == null) checkedAt = Instant.now();
        if (checks == null) checks = List.of();
    }
}
