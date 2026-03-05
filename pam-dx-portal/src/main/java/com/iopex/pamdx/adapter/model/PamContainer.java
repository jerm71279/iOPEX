package com.iopex.pamdx.adapter.model;

import java.util.List;
import java.util.Map;

/**
 * Normalized PAM container — vendor-agnostic representation.
 * Maps to: CyberArk Safe, Secret Server Folder, StrongDM Resource Group.
 */
public record PamContainer(
    String sourceId,
    String sourceVendor,
    String name,
    String description,
    String parent,
    List<Map<String, Object>> members,
    Map<String, Object> properties
) {
    public PamContainer {
        if (sourceId == null || sourceId.isBlank()) {
            throw new IllegalArgumentException("sourceId is required");
        }
        if (description == null) description = "";
        if (parent == null) parent = "";
        if (members == null) members = List.of();
        if (properties == null) properties = Map.of();
    }
}
