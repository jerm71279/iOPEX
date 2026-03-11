package com.iopex.pamdx.adapter.demo;

import com.iopex.pamdx.adapter.PamVendorAdapter;
import com.iopex.pamdx.adapter.model.*;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;

/**
 * In-memory demo adapter — no vault required.
 * Seeds 5 realistic fake accounts. Rotation generates a new fake credential.
 * Always connected. Used for customer demos and local development.
 */
public class DemoAdapter implements PamVendorAdapter {

    private static final String VENDOR = "Demo";

    private final Map<String, String> passwords = new ConcurrentHashMap<>();
    private final Set<String> checkedOut = ConcurrentHashMap.newKeySet();

    public DemoAdapter() {
        passwords.put("demo-account-001", generatePassword());
        passwords.put("demo-account-002", generatePassword());
        passwords.put("demo-account-003", generatePassword());
        passwords.put("demo-account-004", generatePassword());
        passwords.put("demo-account-005", generatePassword());
    }

    @Override public boolean connect()      { return true; }
    @Override public void   disconnect()    { }
    @Override public boolean isConnected()  { return true; }
    @Override public String getVendorName() { return VENDOR; }

    @Override
    public List<PamAccount> getAccounts(Map<String, String> filters) {
        return List.of(
            account("demo-account-001", "svc-webportal",  "web-server-01",  "WinServerLocal"),
            account("demo-account-002", "svc-database",   "db-server-01",   "WinDomain"),
            account("demo-account-003", "svc-api",        "api-server-01",  "UnixSSH"),
            account("demo-account-004", "svc-backup",     "backup-server",  "WinServerLocal"),
            account("demo-account-005", "admin-portal",   "mgmt-server-01", "WinDomain")
        );
    }

    @Override
    public PamAccount getAccount(String accountId) {
        return getAccounts(Map.of()).stream()
            .filter(a -> a.sourceId().equals(accountId))
            .findFirst()
            .orElseThrow(() -> new IllegalArgumentException("Account not found: " + accountId));
    }

    @Override
    public String retrievePassword(String accountId, String reason) {
        return passwords.getOrDefault(accountId, generatePassword());
    }

    @Override
    public String checkOut(String accountId, String reason) {
        checkedOut.add(accountId);
        return passwords.getOrDefault(accountId, generatePassword());
    }

    @Override
    public void checkIn(String accountId) {
        checkedOut.remove(accountId);
    }

    @Override
    public boolean rotatePassword(String accountId) {
        passwords.put(accountId, generatePassword());
        return true;
    }

    @Override
    public List<PamContainer> getContainers() {
        return List.of(
            new PamContainer("safe-web",   VENDOR, "Web Servers Safe",    "", "", List.of(), Map.of()),
            new PamContainer("safe-db",    VENDOR, "Database Safe",       "", "", List.of(), Map.of()),
            new PamContainer("safe-infra", VENDOR, "Infrastructure Safe", "", "", List.of(), Map.of())
        );
    }

    @Override
    public PamContainer createContainer(String name, Map<String, Object> properties) {
        return new PamContainer(UUID.randomUUID().toString(), VENDOR, name,
            "", "", List.of(), properties != null ? properties : Map.of());
    }

    @Override
    public List<PamPlatform> getPlatforms() {
        return List.of(
            new PamPlatform("WinServerLocal", VENDOR, "Windows Server Local", "windows", true, 90, Map.of()),
            new PamPlatform("WinDomain",      VENDOR, "Windows Domain",       "windows", true, 90, Map.of()),
            new PamPlatform("UnixSSH",        VENDOR, "Unix via SSH",         "unix",    true, 90, Map.of())
        );
    }

    @Override
    public List<PamAuditEntry> getAuditLogs(int days) {
        return List.of(
            new PamAuditEntry("evt-001", Instant.now().minusSeconds(3600),
                "CPM_ROTATE", "svc-webportal", "demo-account-001", "safe-web", "SUCCESS", Map.of()),
            new PamAuditEntry("evt-002", Instant.now().minusSeconds(1800),
                "PASSWORD_RETRIEVE", "demo-user", "demo-account-002", "safe-db", "SUCCESS", Map.of())
        );
    }

    @Override
    public PamHealthStatus preflightCheck() {
        return new PamHealthStatus(VENDOR, true, "1.0-demo", Instant.now(), List.of(
            new PamHealthStatus.CheckItem("connectivity", true, "Demo adapter always connected"),
            new PamHealthStatus.CheckItem("auth",         true, "No auth required for demo"),
            new PamHealthStatus.CheckItem("permissions",  true, "Full access in demo mode")
        ));
    }

    // ── Helpers ──────────────────────────────────────────────

    private static String generatePassword() {
        String chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789!@#$%";
        var sb = new StringBuilder(20);
        for (int i = 0; i < 20; i++) {
            sb.append(chars.charAt(ThreadLocalRandom.current().nextInt(chars.length())));
        }
        return sb.toString();
    }

    private static PamAccount account(String id, String username, String address, String platform) {
        return new PamAccount(id, VENDOR, username + "@" + address, username,
            address, "safe-demo", platform, "password", "service",
            true, Instant.now().minusSeconds(86400), Instant.now().minusSeconds(3600),
            Map.of(), Map.of("env", "demo"));
    }
}
