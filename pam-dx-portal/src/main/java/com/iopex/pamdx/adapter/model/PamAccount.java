package com.iopex.pamdx.adapter.model;

import java.time.Instant;
import java.util.Map;

/**
 * Normalized PAM account/secret — vendor-agnostic representation.
 * Maps to: CyberArk Account, Secret Server Secret, StrongDM Resource.
 */
public record PamAccount(
    String sourceId,
    String sourceVendor,
    String name,
    String username,
    String address,
    String containerName,
    String platformType,
    String secretType,
    String accountType,
    boolean managed,
    Instant lastAccessed,
    Instant lastModified,
    Map<String, Object> properties,
    Map<String, String> tags
) {
    public PamAccount {
        if (sourceId == null || sourceId.isBlank()) {
            throw new IllegalArgumentException("sourceId is required");
        }
        if (secretType == null) secretType = "password";
        if (accountType == null) accountType = "human";
        if (properties == null) properties = Map.of();
        if (tags == null) tags = Map.of();
    }
}
