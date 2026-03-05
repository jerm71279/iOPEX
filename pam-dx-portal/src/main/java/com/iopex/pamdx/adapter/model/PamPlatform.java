package com.iopex.pamdx.adapter.model;

import java.util.Map;

/**
 * Normalized PAM platform/template — vendor-agnostic representation.
 * Maps to: CyberArk Platform, Secret Server Secret Template, StrongDM Policy.
 */
public record PamPlatform(
    String sourceId,
    String sourceVendor,
    String name,
    String platformType,
    boolean rotationEnabled,
    int rotationIntervalDays,
    Map<String, Object> properties
) {
    public PamPlatform {
        if (sourceId == null || sourceId.isBlank()) {
            throw new IllegalArgumentException("sourceId is required");
        }
        if (platformType == null) platformType = "";
        if (properties == null) properties = Map.of();
    }
}
