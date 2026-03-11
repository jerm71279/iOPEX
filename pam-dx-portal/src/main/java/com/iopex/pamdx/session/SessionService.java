package com.iopex.pamdx.session;

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

    /** Start a session: check out credential, return masked session record. */
    public SessionRecord startSession(String userId, String accountId, String reason) {
        var account = pamService.getAccount(accountId);
        String rawSecret = pamService.checkOut(accountId, reason);

        var session = new SessionRecord(
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

        scheduleEvent(session.sessionId(), new SessionEvent("SESSION_STARTED",
            "Session started for " + account.name(), 0, session));

        return session;
    }

    /** Get the current state of a session. Throws IllegalArgumentException if not found. */
    public SessionRecord getSession(String sessionId) {
        var s = sessions.get(sessionId);
        if (s == null) throw new IllegalArgumentException("Session not found: " + sessionId);
        return s;
    }

    /** Get all sessions (for demo list view). */
    public List<SessionRecord> getAllSessions() {
        return new ArrayList<>(sessions.values());
    }

    /**
     * End a session: check in the account, trigger rotation asynchronously.
     * Returns immediately — rotation progress is pushed via SSE.
     */
    public void endSession(String sessionId) {
        var session = getSession(sessionId);
        if (session.status() != SessionStatus.ACTIVE) return;

        pamService.checkIn(session.accountId());
        replaceSession(sessionId, session, SessionStatus.ROTATING, false, null, null);
        rotationExecutor.submit(() -> runRotation(sessionId, session.accountId()));
    }

    /** Register an SSE emitter for a session. Called when browser opens /events endpoint. */
    public SseEmitter registerEmitter(String sessionId) {
        var emitter = new SseEmitter(SSE_TIMEOUT_MS);
        emitters.put(sessionId, emitter);
        emitter.onCompletion(() -> emitters.remove(sessionId));
        emitter.onTimeout(() -> emitters.remove(sessionId));
        return emitter;
    }

    // ── Internal ──────────────────────────────────────────────

    /** Animate rotation in steps, then complete. */
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
                String newRaw    = pamService.checkOut(accountId, "post-rotation-verify");
                String newMasked = SessionRecord.mask(newRaw);
                pamService.checkIn(accountId);

                var current = getSession(sessionId);
                var ended = replaceSession(sessionId, current,
                    SessionStatus.ENDED, true, Instant.now(), newMasked);

                pushEvent(sessionId, new SessionEvent("ROTATION_COMPLETE",
                    "Credential rotated successfully", 100, ended));
                pushEvent(sessionId, new SessionEvent("SESSION_ENDED",
                    "Session closed. Old credential is now invalid."));
            } else {
                pushEvent(sessionId, new SessionEvent("ERROR",
                    "Rotation failed — manual intervention required"));
            }

            var emitter = emitters.get(sessionId);
            if (emitter != null) emitter.complete();

        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    private void pushEvent(String sessionId, SessionEvent event) {
        var emitter = emitters.get(sessionId);
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

    /** Delay first event slightly so browser can open SSE connection first. */
    private void scheduleEvent(String sessionId, SessionEvent event) {
        rotationExecutor.submit(() -> {
            try { Thread.sleep(200); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
            pushEvent(sessionId, event);
        });
    }

    private SessionRecord replaceSession(String sessionId, SessionRecord current,
                                          SessionStatus status, boolean rotated,
                                          Instant endedAt, String newMasked) {
        var updated = new SessionRecord(
            current.sessionId(), current.userId(), current.accountId(),
            current.accountName(), current.maskedSecret(),
            current.startedAt(), endedAt, status, rotated, newMasked
        );
        sessions.put(sessionId, updated);
        return updated;
    }
}
