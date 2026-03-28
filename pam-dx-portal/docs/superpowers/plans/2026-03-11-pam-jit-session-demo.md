# PAM JIT Session Demo Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Just-In-Time privileged session demo page to `pam-dx-portal` that shows a user landing on a web page, credentials being injected from the CyberArk vault, and secrets visually rotating out when the session ends.

**Architecture:** A `SessionService` orchestrates the 3-phase lifecycle (start → inject → rotate). A `DemoAdapter` provides realistic in-memory simulation so no live vault is needed. Server-Sent Events (SSE) push rotation progress to the browser in real time, driving a visual animation.

**Tech Stack:** Spring Boot 3.2.5, Java 17, Thymeleaf, Spring MVC `SseEmitter`, JUnit 5, `ConcurrentHashMap` for in-memory session store.

---

## Chunk 1: Extend PamVendorAdapter + DemoAdapter

### Task 1: Add rotation/checkout methods to PamVendorAdapter

**Files:**
- Modify: `src/main/java/com/iopex/pamdx/adapter/PamVendorAdapter.java`

- [ ] **Step 1: Add three new method signatures to the interface**

Add after `retrievePassword()` in `PamVendorAdapter.java`:

```java
// ── Session & Rotation ────────────────────────────────────

/**
 * Trigger immediate CPM password rotation for an account.
 * Maps to: CyberArk POST /Accounts/{id}/Change.
 * Called at session end so the injected credential is immediately invalidated.
 *
 * @param accountId the account to rotate
 * @return true if rotation was successfully scheduled
 */
boolean rotatePassword(String accountId);

/**
 * Check out an account for exclusive use (dual-control / one-at-a-time access).
 * Returns the credential. Must be followed by {@link #checkIn(String)} on session end.
 *
 * @param accountId the account to check out
 * @param reason    business justification
 * @return the secret value
 */
String checkOut(String accountId, String reason);

/**
 * Release the exclusive lock on a checked-out account.
 * Triggers rotation for accounts configured with automatic change on check-in.
 *
 * @param accountId the account to check in
 */
void checkIn(String accountId);
```

- [ ] **Step 2: Verify existing adapter stubs compile**

The contract test imports `CyberArkAdapter`, `DelineaAdapter`, `StrongDmAdapter`. These will fail to compile until they implement the new methods. We'll fix that in Task 2.

---

### Task 2: Create DemoAdapter

**Files:**
- Create: `src/main/java/com/iopex/pamdx/adapter/demo/DemoAdapter.java`
- Modify: `src/test/java/com/iopex/pamdx/adapter/PamVendorAdapterContractTest.java`

The `DemoAdapter` simulates a vault in memory. It seeds 5 demo accounts with realistic fake credentials. Rotation replaces the stored password with a new generated one.

- [ ] **Step 1: Write the failing contract test for DemoAdapter**

Add to `PamVendorAdapterContractTest.java`:

```java
import com.iopex.pamdx.adapter.demo.DemoAdapter;

@Test
void demoAdapterReturnsCorrectVendorName() {
    PamVendorAdapter adapter = new DemoAdapter();
    assertEquals("Demo", adapter.getVendorName());
    assertTrue(adapter.isConnected()); // DemoAdapter is always connected
}

@Test
void demoAdapterCheckOutReturnsCredential() {
    DemoAdapter adapter = new DemoAdapter();
    String secret = adapter.checkOut("demo-account-001", "test reason");
    assertNotNull(secret);
    assertFalse(secret.isBlank());
}

@Test
void demoAdapterRotatePasswordChangesCredential() {
    DemoAdapter adapter = new DemoAdapter();
    String before = adapter.checkOut("demo-account-001", "test");
    adapter.checkIn("demo-account-001");
    boolean rotated = adapter.rotatePassword("demo-account-001");
    assertTrue(rotated);
    String after = adapter.checkOut("demo-account-001", "test after rotation");
    assertNotEquals(before, after, "Credential should change after rotation");
}

@Test
void demoAdapterPreflightAlwaysPasses() {
    DemoAdapter adapter = new DemoAdapter();
    PamHealthStatus health = adapter.preflightCheck();
    assertEquals("Demo", health.vendor());
    assertTrue(health.connected());
    assertTrue(health.checks().stream().allMatch(PamHealthStatus.CheckItem::passed));
}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd pam-dx-portal
mvn test -pl . -Dtest=PamVendorAdapterContractTest -q 2>&1 | tail -20
```

Expected: COMPILE ERROR — `DemoAdapter` not found.

- [ ] **Step 3: Create DemoAdapter**

Create `src/main/java/com/iopex/pamdx/adapter/demo/DemoAdapter.java`:

```java
package com.iopex.pamdx.adapter.demo;

import com.iopex.pamdx.adapter.PamVendorAdapter;
import com.iopex.pamdx.adapter.model.*;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;

/**
 * In-memory demo adapter — no vault required.
 * Seeds realistic fake accounts. Rotation generates a new fake credential.
 * Always connected. Used for customer demos and local development.
 */
public class DemoAdapter implements PamVendorAdapter {

    private static final String VENDOR = "Demo";

    private final Map<String, String> passwords = new ConcurrentHashMap<>();
    private final Set<String> checkedOut = ConcurrentHashMap.newKeySet();

    public DemoAdapter() {
        // Seed 5 realistic demo accounts
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
            new PamContainer("safe-web",  VENDOR, "Web Servers Safe",   Map.of()),
            new PamContainer("safe-db",   VENDOR, "Database Safe",      Map.of()),
            new PamContainer("safe-infra",VENDOR, "Infrastructure Safe", Map.of())
        );
    }

    @Override
    public PamContainer createContainer(String name, Map<String, Object> properties) {
        return new PamContainer(UUID.randomUUID().toString(), VENDOR, name, properties);
    }

    @Override
    public List<PamPlatform> getPlatforms() {
        return List.of(
            new PamPlatform("WinServerLocal", VENDOR, "Windows Server Local"),
            new PamPlatform("WinDomain",      VENDOR, "Windows Domain"),
            new PamPlatform("UnixSSH",        VENDOR, "Unix via SSH")
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
        StringBuilder sb = new StringBuilder(20);
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
```

- [ ] **Step 4: Add `rotatePassword`, `checkOut`, `checkIn` stub implementations to existing adapters**

`CyberArkAdapter`, `DelineaAdapter`, `StrongDmAdapter` must implement the new interface methods. Add stub bodies that throw `UnsupportedOperationException` (real implementations come later):

For each adapter class (find them in `src/main/java/.../adapter/cyberark/`, `delinea/`, `strongdm/`):

```java
@Override
public boolean rotatePassword(String accountId) {
    throw new UnsupportedOperationException("rotatePassword not yet implemented for " + getVendorName());
}

@Override
public String checkOut(String accountId, String reason) {
    // Fall back to retrieve — most vendors don't require explicit check-out
    return retrievePassword(accountId, reason);
}

@Override
public void checkIn(String accountId) {
    // No-op for adapters without exclusive check-out
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
mvn test -Dtest=PamVendorAdapterContractTest -q 2>&1 | tail -10
```

Expected: `BUILD SUCCESS`, all 8 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/main/java/com/iopex/pamdx/adapter/ \
        src/test/java/com/iopex/pamdx/adapter/
git commit -m "feat: add rotatePassword/checkOut/checkIn to adapter + DemoAdapter"
```

---

## Chunk 2: Session Domain Model + Service

### Task 3: Session model

**Files:**
- Create: `src/main/java/com/iopex/pamdx/session/SessionStatus.java`
- Create: `src/main/java/com/iopex/pamdx/session/SessionRecord.java`
- Create: `src/main/java/com/iopex/pamdx/session/SessionEvent.java`

- [ ] **Step 1: Create SessionStatus enum**

```java
package com.iopex.pamdx.session;

public enum SessionStatus {
    ACTIVE,     // credential injected, session live
    ROTATING,   // session ended, rotation in progress
    ENDED,      // rotation complete, session closed
    EXPIRED     // timed out before explicit end
}
```

- [ ] **Step 2: Create SessionRecord**

```java
package com.iopex.pamdx.session;

import java.time.Instant;

/**
 * Immutable snapshot of a privileged session at a point in time.
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
```

- [ ] **Step 3: Create SessionEvent (SSE payload)**

```java
package com.iopex.pamdx.session;

/**
 * Event pushed via SSE to the demo page.
 * type: SESSION_STARTED | CREDENTIAL_INJECTED | ROTATION_STARTING |
 *        ROTATION_PROGRESS | ROTATION_COMPLETE | SESSION_ENDED | ERROR
 */
public record SessionEvent(
    String type,
    String message,
    int progressPct,    // 0-100, used for ROTATION_PROGRESS events
    Object data         // optional structured payload (SessionRecord, etc.)
) {
    public SessionEvent(String type, String message) {
        this(type, message, 0, null);
    }
}
```

---

### Task 4: SessionService

**Files:**
- Create: `src/main/java/com/iopex/pamdx/session/SessionService.java`
- Create: `src/test/java/com/iopex/pamdx/session/SessionServiceTest.java`

- [ ] **Step 1: Write failing unit tests**

Create `src/test/java/com/iopex/pamdx/session/SessionServiceTest.java`:

```java
package com.iopex.pamdx.session;

import com.iopex.pamdx.adapter.demo.DemoAdapter;
import com.iopex.pamdx.service.PamService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class SessionServiceTest {

    private SessionService sessionService;

    @BeforeEach
    void setUp() {
        PamService pamService = new PamService(new DemoAdapter());
        sessionService = new SessionService(pamService);
    }

    @Test
    void startSessionCreatesActiveRecord() {
        SessionRecord session = sessionService.startSession("user-alice", "demo-account-001", "test access");
        assertNotNull(session.sessionId());
        assertEquals("user-alice", session.userId());
        assertEquals("demo-account-001", session.accountId());
        assertEquals(SessionStatus.ACTIVE, session.status());
        assertNotNull(session.maskedSecret());
        assertFalse(session.maskedSecret().isBlank());
        assertNull(session.endedAt());
        assertFalse(session.rotationTriggered());
    }

    @Test
    void maskedSecretNeverExposesFullCredential() {
        SessionRecord session = sessionService.startSession("user-bob", "demo-account-002", "test");
        String masked = session.maskedSecret();
        // Should contain bullet characters, not the full 20-char password
        assertTrue(masked.contains("••"), "Secret should be partially masked");
        assertTrue(masked.length() < 20, "Masked form should be shorter representation");
    }

    @Test
    void getSessionReturnsActiveSession() {
        SessionRecord started = sessionService.startSession("user-carol", "demo-account-003", "test");
        SessionRecord retrieved = sessionService.getSession(started.sessionId());
        assertEquals(started.sessionId(), retrieved.sessionId());
    }

    @Test
    void getSessionThrowsForUnknownId() {
        assertThrows(IllegalArgumentException.class,
            () -> sessionService.getSession("nonexistent-id"));
    }

    @Test
    void endSessionTriggersRotation() throws InterruptedException {
        SessionRecord started = sessionService.startSession("user-dan", "demo-account-004", "test");
        sessionService.endSession(started.sessionId());

        // Give the async rotation a moment to complete
        Thread.sleep(4000);

        SessionRecord ended = sessionService.getSession(started.sessionId());
        assertEquals(SessionStatus.ENDED, ended.status());
        assertTrue(ended.rotationTriggered());
        assertNotNull(ended.endedAt());
        assertNotNull(ended.rotationNewMasked());
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
mvn test -Dtest=SessionServiceTest -q 2>&1 | tail -10
```

Expected: COMPILE ERROR — `SessionService` not found.

- [ ] **Step 3: Implement SessionService**

Create `src/main/java/com/iopex/pamdx/session/SessionService.java`:

```java
package com.iopex.pamdx.session;

import com.iopex.pamdx.adapter.model.PamAccount;
import com.iopex.pamdx.service.PamService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;

/**
 * Manages privileged session lifecycle: start → inject → rotate.
 *
 * Sessions are stored in memory (demo mode). Each session gets an SSE emitter
 * that pushes rotation progress events to the browser in real time.
 *
 * Thread safety: ConcurrentHashMap for sessions + emitters. Rotation runs
 * on a background thread pool so the end-session endpoint returns immediately.
 */
@Service
public class SessionService {

    private static final Logger log = LoggerFactory.getLogger(SessionService.class);
    private static final long SSE_TIMEOUT_MS = 300_000L; // 5 minutes

    private final PamService pamService;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final Map<String, SessionRecord> sessions = new ConcurrentHashMap<>();
    private final Map<String, SseEmitter> emitters = new ConcurrentHashMap<>();
    private final ExecutorService rotationExecutor = Executors.newCachedThreadPool();

    public SessionService(PamService pamService) {
        this.pamService = pamService;
    }

    // ── Public API ────────────────────────────────────────────

    /** Start a session: check out credential, log start, return masked session record. */
    public SessionRecord startSession(String userId, String accountId, String reason) {
        PamAccount account = pamService.getAccount(accountId);
        String rawSecret = pamService.checkOut(accountId, reason);

        SessionRecord session = new SessionRecord(
            UUID.randomUUID().toString(),
            userId,
            accountId,
            account.name(),
            SessionRecord.mask(rawSecret),
            Instant.now(),
            null,
            SessionStatus.ACTIVE,
            false,
            null
        );

        sessions.put(session.sessionId(), session);
        log.info("Session started: {} for account {} by {}", session.sessionId(), accountId, userId);

        // Push initial events to any waiting emitter (won't exist yet — emitter registers after)
        scheduleEvent(session.sessionId(), new SessionEvent("SESSION_STARTED",
            "Session started for " + account.name(), 0, session));

        return session;
    }

    /** Get the current state of a session. */
    public SessionRecord getSession(String sessionId) {
        SessionRecord s = sessions.get(sessionId);
        if (s == null) throw new IllegalArgumentException("Session not found: " + sessionId);
        return s;
    }

    /** Get all sessions (for the demo list view). */
    public List<SessionRecord> getAllSessions() {
        return new ArrayList<>(sessions.values());
    }

    /**
     * End a session: check in the account, then run rotation asynchronously.
     * Returns immediately — rotation progress is pushed via SSE.
     */
    public void endSession(String sessionId) {
        SessionRecord session = getSession(sessionId);
        if (session.status() != SessionStatus.ACTIVE) return;

        pamService.checkIn(session.accountId());
        updateSession(sessionId, session, SessionStatus.ROTATING, false, null, null);

        rotationExecutor.submit(() -> runRotation(sessionId, session.accountId()));
    }

    /** Register an SSE emitter for a session (called when browser opens /events endpoint). */
    public SseEmitter registerEmitter(String sessionId) {
        SseEmitter emitter = new SseEmitter(SSE_TIMEOUT_MS);
        emitters.put(sessionId, emitter);
        emitter.onCompletion(() -> emitters.remove(sessionId));
        emitter.onTimeout(() -> emitters.remove(sessionId));
        return emitter;
    }

    // ── Internal ──────────────────────────────────────────────

    /** Animate rotation in 4 steps, then complete. */
    private void runRotation(String sessionId, String accountId) {
        try {
            pushEvent(sessionId, new SessionEvent("ROTATION_STARTING", "Initiating CPM rotation…"));
            Thread.sleep(800);

            pushEvent(sessionId, new SessionEvent("ROTATION_PROGRESS", "Generating new credential…", 25, null));
            Thread.sleep(800);

            pushEvent(sessionId, new SessionEvent("ROTATION_PROGRESS", "Pushing to vault…", 55, null));
            Thread.sleep(800);

            boolean ok = pamService.rotatePassword(accountId);

            pushEvent(sessionId, new SessionEvent("ROTATION_PROGRESS", "Validating rotation…", 85, null));
            Thread.sleep(600);

            if (ok) {
                // Fetch the new (rotated) credential for display
                String newRaw    = pamService.checkOut(accountId, "post-rotation-verify");
                String newMasked = SessionRecord.mask(newRaw);
                pamService.checkIn(accountId);

                SessionRecord current = getSession(sessionId);
                SessionRecord ended = updateSession(sessionId, current,
                    SessionStatus.ENDED, true, Instant.now(), newMasked);

                pushEvent(sessionId, new SessionEvent("ROTATION_COMPLETE",
                    "Credential rotated successfully", 100, ended));
                pushEvent(sessionId, new SessionEvent("SESSION_ENDED",
                    "Session closed. Old credential is now invalid."));
            } else {
                pushEvent(sessionId, new SessionEvent("ERROR", "Rotation failed — manual intervention required"));
            }

            SseEmitter emitter = emitters.get(sessionId);
            if (emitter != null) emitter.complete();

        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    private void pushEvent(String sessionId, SessionEvent event) {
        SseEmitter emitter = emitters.get(sessionId);
        if (emitter == null) return;
        try {
            emitter.send(SseEmitter.event()
                .name(event.type())
                .data(objectMapper.writeValueAsString(event)));
        } catch (IOException e) {
            log.warn("SSE send failed for session {}: {}", sessionId, e.getMessage());
            emitters.remove(sessionId);
        }
    }

    private void scheduleEvent(String sessionId, SessionEvent event) {
        // Slight delay so the browser can register its emitter first
        rotationExecutor.submit(() -> {
            try { Thread.sleep(100); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
            pushEvent(sessionId, event);
        });
    }

    private SessionRecord updateSession(String sessionId, SessionRecord current,
                                        SessionStatus status, boolean rotated,
                                        Instant endedAt, String newMasked) {
        SessionRecord updated = new SessionRecord(
            current.sessionId(), current.userId(), current.accountId(),
            current.accountName(), current.maskedSecret(),
            current.startedAt(), endedAt, status, rotated, newMasked
        );
        sessions.put(sessionId, updated);
        return updated;
    }
}
```

- [ ] **Step 4: Add checkOut/checkIn/rotatePassword to PamService**

Add to `src/main/java/com/iopex/pamdx/service/PamService.java`:

```java
public String checkOut(String accountId, String reason) {
    log.info("Check-out requested for account {} — reason: {}", accountId, reason);
    return adapter.checkOut(accountId, reason);
}

public void checkIn(String accountId) {
    log.info("Check-in for account {}", accountId);
    adapter.checkIn(accountId);
}

public boolean rotatePassword(String accountId) {
    log.info("Rotation requested for account {}", accountId);
    return adapter.rotatePassword(accountId);
}

public PamAccount getAccount(String accountId) {
    return adapter.getAccount(accountId);
}
```

- [ ] **Step 5: Run tests**

```bash
mvn test -Dtest="SessionServiceTest,PamVendorAdapterContractTest" -q 2>&1 | tail -15
```

Expected: `BUILD SUCCESS`.

- [ ] **Step 6: Commit**

```bash
git add src/main/java/com/iopex/pamdx/session/ \
        src/main/java/com/iopex/pamdx/service/PamService.java \
        src/test/java/com/iopex/pamdx/session/
git commit -m "feat: session domain model + SessionService with async rotation"
```

---

## Chunk 3: REST Controller + Demo Web Page

### Task 5: SessionController

**Files:**
- Create: `src/main/java/com/iopex/pamdx/session/SessionController.java`

- [ ] **Step 1: Create SessionController**

```java
package com.iopex.pamdx.session;

import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;
import java.util.Map;

/**
 * REST API + SSE endpoints for the JIT session demo.
 *
 * POST /api/sessions              — start session, returns SessionRecord
 * POST /api/sessions/{id}/end     — end session (triggers async rotation), returns 202
 * GET  /api/sessions/{id}         — get session state
 * GET  /api/sessions              — list all sessions
 * GET  /api/sessions/{id}/events  — SSE stream for rotation progress
 * GET  /session-demo              — serve the demo page (redirect to static)
 */
@RestController
@RequestMapping("/api/sessions")
public class SessionController {

    private final SessionService sessionService;

    public SessionController(SessionService sessionService) {
        this.sessionService = sessionService;
    }

    @PostMapping
    public ResponseEntity<SessionRecord> startSession(@RequestBody StartSessionRequest req) {
        SessionRecord session = sessionService.startSession(
            req.userId(), req.accountId(), req.reason());
        return ResponseEntity.ok(session);
    }

    @PostMapping("/{id}/end")
    public ResponseEntity<Void> endSession(@PathVariable String id) {
        sessionService.endSession(id);
        return ResponseEntity.accepted().build(); // 202 — rotation is async
    }

    @GetMapping("/{id}")
    public ResponseEntity<SessionRecord> getSession(@PathVariable String id) {
        try {
            return ResponseEntity.ok(sessionService.getSession(id));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.notFound().build();
        }
    }

    @GetMapping
    public ResponseEntity<List<SessionRecord>> listSessions() {
        return ResponseEntity.ok(sessionService.getAllSessions());
    }

    @GetMapping(value = "/{id}/events", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter streamEvents(@PathVariable String id) {
        return sessionService.registerEmitter(id);
    }

    // ── Request body ──────────────────────────────────────────

    public record StartSessionRequest(String userId, String accountId, String reason) {}
}
```

---

### Task 6: Demo Web Page

**Files:**
- Create: `src/main/resources/static/session-demo.html`

This is a self-contained HTML page. No framework — just vanilla JS + CSS.
It shows: account selector → start session → credential display with mask → "End Session" button → real-time rotation animation (progress bar, old credential struck through, new masked credential revealed).

- [ ] **Step 1: Create session-demo.html**

Create `src/main/resources/static/session-demo.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>PAM JIT Session Demo — iOPEX</title>
  <style>
    :root {
      --bg: #0d1117; --surface: #161b22; --border: #30363d;
      --text: #e6edf3; --muted: #8b949e; --blue: #58a6ff;
      --green: #3fb950; --yellow: #d29922; --red: #f85149;
      --purple: #bc8cff;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif;
           min-height: 100vh; padding: 2rem; }
    h1 { color: var(--blue); font-size: 1.5rem; margin-bottom: 0.25rem; }
    .subtitle { color: var(--muted); font-size: 0.85rem; margin-bottom: 2rem; }
    .card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
            padding: 1.5rem; margin-bottom: 1.5rem; }
    label { display: block; font-size: 0.8rem; color: var(--muted); margin-bottom: 0.35rem; }
    select, input { width: 100%; padding: 0.55rem 0.75rem; background: var(--bg);
                    border: 1px solid var(--border); border-radius: 6px; color: var(--text);
                    font-size: 0.9rem; margin-bottom: 1rem; }
    button { padding: 0.6rem 1.5rem; border-radius: 6px; border: none; cursor: pointer;
             font-size: 0.9rem; font-weight: 600; transition: opacity 0.2s; }
    button:hover { opacity: 0.85; }
    .btn-start  { background: var(--green); color: #000; }
    .btn-end    { background: var(--red);   color: #fff; }
    .btn-end:disabled { opacity: 0.4; cursor: not-allowed; }

    /* Credential display */
    .cred-box { background: var(--bg); border: 1px solid var(--border); border-radius: 6px;
                padding: 1rem 1.25rem; font-family: monospace; font-size: 1.1rem;
                display: flex; align-items: center; gap: 1rem; margin: 1rem 0; }
    .cred-value { flex: 1; letter-spacing: 0.1em; }
    .cred-label { font-size: 0.7rem; color: var(--muted); }
    .old-cred { text-decoration: line-through; color: var(--red); opacity: 0.7; }
    .new-cred { color: var(--green); }

    /* Rotation progress */
    .progress-wrap { margin: 1rem 0; }
    .progress-bar  { height: 8px; background: var(--border); border-radius: 4px; overflow: hidden; }
    .progress-fill { height: 100%; background: var(--blue); border-radius: 4px;
                     transition: width 0.6s ease; width: 0%; }
    .progress-msg  { font-size: 0.8rem; color: var(--muted); margin-top: 0.4rem; }

    /* Status badge */
    .badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 20px;
             font-size: 0.75rem; font-weight: 600; }
    .badge-active   { background: rgba(63,185,80,0.2);  color: var(--green); }
    .badge-rotating { background: rgba(210,153,34,0.2); color: var(--yellow); }
    .badge-ended    { background: rgba(139,148,158,0.2); color: var(--muted); }

    /* Event log */
    .log-entries { max-height: 260px; overflow-y: auto; }
    .log-entry { padding: 0.5rem 0; border-bottom: 1px solid var(--border);
                 font-size: 0.82rem; display: flex; gap: 0.75rem; }
    .log-time  { color: var(--muted); white-space: nowrap; font-family: monospace; }
    .log-type  { font-weight: 700; min-width: 8rem; }
    .type-SESSION_STARTED   { color: var(--blue); }
    .type-CREDENTIAL_INJECTED { color: var(--green); }
    .type-ROTATION_STARTING { color: var(--yellow); }
    .type-ROTATION_PROGRESS { color: var(--yellow); }
    .type-ROTATION_COMPLETE { color: var(--green); }
    .type-SESSION_ENDED     { color: var(--muted); }
    .type-ERROR             { color: var(--red); }

    .hidden { display: none; }
    #session-panel { display: none; }
  </style>
</head>
<body>

<h1>🔐 PAM JIT Session Demo</h1>
<p class="subtitle">iOPEX · CyberArk Privileged Access · Secret Injection + Auto-Rotation</p>

<!-- Start Session -->
<div class="card" id="start-panel">
  <h2 style="font-size:1rem; margin-bottom:1rem; color:var(--muted);">New Privileged Session</h2>
  <label>Account</label>
  <select id="accountId">
    <option value="demo-account-001">svc-webportal @ web-server-01 (WinServerLocal)</option>
    <option value="demo-account-002">svc-database @ db-server-01 (WinDomain)</option>
    <option value="demo-account-003">svc-api @ api-server-01 (UnixSSH)</option>
    <option value="demo-account-004">svc-backup @ backup-server (WinServerLocal)</option>
    <option value="demo-account-005">admin-portal @ mgmt-server-01 (WinDomain)</option>
  </select>
  <label>User ID</label>
  <input id="userId" value="demo-admin" placeholder="e.g. john.smith@company.com" />
  <label>Business Reason</label>
  <input id="reason" value="Emergency access - incident #INC-4821" />
  <button class="btn-start" onclick="startSession()">Start Privileged Session</button>
</div>

<!-- Active Session -->
<div class="card" id="session-panel">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
    <h2 style="font-size:1rem; color:var(--muted);">Active Session</h2>
    <span id="status-badge" class="badge badge-active">ACTIVE</span>
  </div>

  <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:1rem;">
    <div>
      <div class="cred-label">SESSION ID</div>
      <div id="session-id" style="font-family:monospace; font-size:0.8rem; color:var(--muted);"></div>
    </div>
    <div>
      <div class="cred-label">ACCOUNT</div>
      <div id="session-account" style="font-size:0.9rem;"></div>
    </div>
  </div>

  <div class="cred-label">INJECTED CREDENTIAL</div>
  <div class="cred-box">
    <div>
      <div id="old-cred" class="cred-value"></div>
      <div id="new-cred" class="cred-value new-cred hidden"></div>
    </div>
    <div style="text-align:right">
      <div id="vault-source" class="cred-label" style="color:var(--blue);">⬡ CyberArk Vault</div>
      <div id="cred-status" class="cred-label">ACTIVE</div>
    </div>
  </div>

  <div class="progress-wrap" id="rotation-wrap" style="display:none;">
    <div class="progress-bar"><div class="progress-fill" id="progress-fill"></div></div>
    <div class="progress-msg" id="progress-msg"></div>
  </div>

  <button class="btn-end" id="end-btn" onclick="endSession()">End Session &amp; Rotate Secret</button>
</div>

<!-- Event Log -->
<div class="card" id="log-panel" style="display:none;">
  <h2 style="font-size:1rem; margin-bottom:1rem; color:var(--muted);">Session Audit Log</h2>
  <div class="log-entries" id="log-entries"></div>
</div>

<script>
  let currentSessionId = null;
  let eventSource = null;

  async function startSession() {
    const accountId = document.getElementById('accountId').value;
    const userId    = document.getElementById('userId').value;
    const reason    = document.getElementById('reason').value;

    const res = await fetch('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ userId, accountId, reason })
    });
    const session = await res.json();
    currentSessionId = session.sessionId;

    document.getElementById('start-panel').style.display = 'none';
    document.getElementById('session-panel').style.display = 'block';
    document.getElementById('log-panel').style.display = 'block';

    document.getElementById('session-id').textContent = session.sessionId;
    document.getElementById('session-account').textContent = session.accountName;
    document.getElementById('old-cred').textContent = session.maskedSecret;

    addLogEntry('SESSION_STARTED', 'Session started for ' + session.accountName);
    addLogEntry('CREDENTIAL_INJECTED', 'Secret retrieved from CyberArk vault → ' + session.maskedSecret);

    connectSSE(currentSessionId);
  }

  async function endSession() {
    document.getElementById('end-btn').disabled = true;
    document.getElementById('rotation-wrap').style.display = 'block';
    updateStatus('ROTATING');

    await fetch('/api/sessions/' + currentSessionId + '/end', { method: 'POST' });
    addLogEntry('ROTATION_STARTING', 'CPM rotation initiated by user');
  }

  function connectSSE(sessionId) {
    if (eventSource) eventSource.close();
    eventSource = new EventSource('/api/sessions/' + sessionId + '/events');

    const handlers = {
      SESSION_STARTED:      (e) => { /* already shown */ },
      CREDENTIAL_INJECTED:  (e) => { },
      ROTATION_STARTING:    (e) => {
        addLogEntry(e.type, e.message);
        setProgress(5, e.message);
      },
      ROTATION_PROGRESS:    (e) => {
        addLogEntry(e.type, e.message);
        setProgress(e.progressPct, e.message);
      },
      ROTATION_COMPLETE:    (e) => {
        addLogEntry(e.type, e.message);
        setProgress(100, 'Rotation complete ✓');
        updateStatus('ENDED');
        const data = e.data ? (typeof e.data === 'string' ? JSON.parse(e.data) : e.data) : null;
        if (data && data.rotationNewMasked) showNewCred(data.rotationNewMasked);
        document.getElementById('cred-status').textContent = 'ROTATED — INVALID';
        document.getElementById('cred-status').style.color = 'var(--red)';
      },
      SESSION_ENDED:        (e) => {
        addLogEntry(e.type, e.message);
        eventSource.close();
      },
      ERROR:                (e) => {
        addLogEntry(e.type, e.message);
        document.getElementById('end-btn').disabled = false;
      }
    };

    // SSE events come as named events matching SessionEvent.type
    Object.keys(handlers).forEach(type => {
      eventSource.addEventListener(type, (raw) => {
        const payload = JSON.parse(raw.data);
        handlers[type](payload);
      });
    });
  }

  function setProgress(pct, msg) {
    document.getElementById('progress-fill').style.width = pct + '%';
    document.getElementById('progress-msg').textContent = msg;
  }

  function showNewCred(newMasked) {
    const oldEl = document.getElementById('old-cred');
    oldEl.classList.add('old-cred');
    const newEl = document.getElementById('new-cred');
    newEl.textContent = newMasked;
    newEl.classList.remove('hidden');
    document.getElementById('vault-source').textContent = '⬡ CyberArk Vault (Rotated)';
  }

  function updateStatus(status) {
    const badge = document.getElementById('status-badge');
    badge.className = 'badge badge-' + status.toLowerCase();
    badge.textContent = status;
  }

  function addLogEntry(type, message) {
    const container = document.getElementById('log-entries');
    const now = new Date().toISOString().replace('T', ' ').substring(0, 19);
    const div = document.createElement('div');
    div.className = 'log-entry';
    div.innerHTML = `
      <span class="log-time">${now}</span>
      <span class="log-type type-${type}">${type}</span>
      <span>${message}</span>`;
    container.prepend(div);
  }
</script>
</body>
</html>
```

- [ ] **Step 2: Test the page manually**

```bash
# In pam-dx-portal/
mvn spring-boot:run -Dspring-boot.run.arguments="--pam.adapter=demo"
```

Open `http://localhost:8080/session-demo.html` in a browser.

**Verify the full flow:**
1. Select an account, click "Start Privileged Session"
2. Session panel appears with masked credential
3. Audit log shows `SESSION_STARTED` + `CREDENTIAL_INJECTED`
4. Click "End Session & Rotate Secret"
5. Progress bar animates 0→25→55→85→100%
6. Old credential gets struck through in red
7. New masked credential appears in green
8. Status badge changes ACTIVE → ROTATING → ENDED
9. Log shows all rotation events

- [ ] **Step 3: Run all tests**

```bash
mvn test -q 2>&1 | tail -15
```

Expected: `BUILD SUCCESS`.

- [ ] **Step 4: Commit**

```bash
git add src/main/java/com/iopex/pamdx/session/SessionController.java \
        src/main/resources/static/session-demo.html
git commit -m "feat: JIT session demo page with SSE rotation animation"
```

---

## Chunk 4: Wire DemoAdapter via Configuration

### Task 7: Configure DemoAdapter as default bean

**Files:**
- Create: `src/main/java/com/iopex/pamdx/config/AdapterConfig.java`
- Create: `src/main/resources/application.properties`

The `PamService` needs a `PamVendorAdapter` bean injected. We need `AdapterConfig` to wire the correct implementation based on a property. `demo` is the default so the app starts with no vault connection needed.

- [ ] **Step 1: Create AdapterConfig**

```java
package com.iopex.pamdx.config;

import com.iopex.pamdx.adapter.PamVendorAdapter;
import com.iopex.pamdx.adapter.demo.DemoAdapter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class AdapterConfig {

    @Value("${pam.adapter:demo}")
    private String adapterType;

    @Bean
    public PamVendorAdapter pamVendorAdapter() {
        return switch (adapterType.toLowerCase()) {
            case "demo" -> new DemoAdapter();
            // "cyberark", "delinea", "strongdm" wired here in future
            default -> throw new IllegalArgumentException("Unknown PAM adapter: " + adapterType);
        };
    }
}
```

- [ ] **Step 2: Set default in application.properties**

```properties
# PAM adapter: demo | cyberark | delinea | strongdm
pam.adapter=demo
server.port=8080
spring.thymeleaf.cache=false
```

- [ ] **Step 3: Run full test suite + start app**

```bash
mvn test -q && mvn spring-boot:run
```

- [ ] **Step 4: Final commit**

```bash
git add src/main/java/com/iopex/pamdx/config/ \
        src/main/resources/application.properties
git commit -m "feat: AdapterConfig + demo mode default — full JIT session flow complete"
```

---

## Summary

After all tasks complete:

| Endpoint | Description |
|---|---|
| `GET /session-demo.html` | Demo page — visual rotation UI |
| `POST /api/sessions` | Start session → inject credential |
| `POST /api/sessions/{id}/end` | End session → trigger rotation (async) |
| `GET /api/sessions/{id}/events` | SSE stream — rotation progress events |
| `GET /api/sessions/{id}` | Get session state |

**New files created:**
- `adapter/demo/DemoAdapter.java`
- `session/SessionStatus.java`
- `session/SessionRecord.java`
- `session/SessionEvent.java`
- `session/SessionService.java`
- `session/SessionController.java`
- `config/AdapterConfig.java`
- `resources/static/session-demo.html`
- `resources/application.properties`

**Modified:**
- `adapter/PamVendorAdapter.java` — +3 methods
- `service/PamService.java` — +4 delegates
- `adapter/PamVendorAdapterContractTest.java` — +4 DemoAdapter tests
