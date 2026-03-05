package com.iopex.pamdx.adapter;

import com.iopex.pamdx.adapter.model.*;
import java.util.List;
import java.util.Map;

/**
 * Vendor-agnostic PAM adapter interface.
 *
 * <p>This is the core abstraction of the Digital Experience layer. Every PAM vendor
 * (CyberArk, Delinea, StrongDM, BeyondTrust, HashiCorp Vault, etc.) implements
 * this interface. The portal and API gateway call only these methods — never
 * vendor-specific APIs directly.</p>
 *
 * <p>To add a new vendor, implement this interface and register the bean in
 * {@link com.iopex.pamdx.config.AdapterConfig}.</p>
 *
 * <p>Mirrors the Python {@code SourceAdapter} ABC in
 * {@code core/source_adapters.py} with normalized data models.</p>
 */
public interface PamVendorAdapter {

    // ── Lifecycle ──────────────────────────────────────────────

    /**
     * Establish connection to the PAM vendor. Handles OAuth2 token exchange,
     * session creation, or API key validation depending on vendor.
     *
     * @return true if connection succeeded
     */
    boolean connect();

    /**
     * Close connection and release resources. Zero out any in-memory credentials.
     */
    void disconnect();

    /**
     * Check if the adapter has an active, authenticated connection.
     */
    boolean isConnected();

    // ── Accounts (Secrets) ────────────────────────────────────

    /**
     * List accounts with optional filters. Handles pagination internally.
     *
     * @param filters vendor-interpreted filter map (e.g., "search", "container", "platform")
     * @return normalized account list
     */
    List<PamAccount> getAccounts(Map<String, String> filters);

    /**
     * Get a single account by its vendor-specific ID.
     *
     * @param accountId CyberArk account ID, SS secret ID, or StrongDM resource ID
     */
    PamAccount getAccount(String accountId);

    /**
     * Retrieve the actual password/secret value for an account.
     * This is a privileged operation — audit logged.
     *
     * @param accountId the account to retrieve
     * @param reason    business justification (required by most PAM vendors)
     * @return the secret value
     */
    String retrievePassword(String accountId, String reason);

    // ── Containers (Safes / Folders) ──────────────────────────

    /**
     * List all containers. Maps to CyberArk Safes, SS Folders, StrongDM Resource Groups.
     */
    List<PamContainer> getContainers();

    /**
     * Create a new container.
     *
     * @param name       container name
     * @param properties vendor-specific properties (retention, CPM, permissions)
     */
    PamContainer createContainer(String name, Map<String, Object> properties);

    // ── Platforms (Templates) ─────────────────────────────────

    /**
     * List all platforms/templates. Maps to CyberArk Platforms, SS Secret Templates.
     */
    List<PamPlatform> getPlatforms();

    // ── Audit ─────────────────────────────────────────────────

    /**
     * Retrieve audit log entries for the last N days.
     *
     * @param days lookback period
     */
    List<PamAuditEntry> getAuditLogs(int days);

    // ── Health ────────────────────────────────────────────────

    /**
     * Run preflight/health checks: connectivity, auth, permissions, version.
     */
    PamHealthStatus preflightCheck();

    // ── Identity ──────────────────────────────────────────────

    /**
     * Return the vendor name (e.g., "CyberArk", "Delinea", "StrongDM").
     */
    String getVendorName();
}
