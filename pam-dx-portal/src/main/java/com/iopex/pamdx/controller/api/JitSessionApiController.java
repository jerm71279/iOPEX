package com.iopex.pamdx.controller.api;

import com.iopex.pamdx.session.SessionRecord;
import com.iopex.pamdx.session.SessionService;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;

/**
 * REST API + SSE endpoints for the JIT privileged session demo.
 *
 * POST /api/sessions              — start session, returns SessionRecord (JSON)
 * POST /api/sessions/{id}/end     — end session (triggers async rotation), returns 202
 * GET  /api/sessions/{id}         — get current session state
 * GET  /api/sessions              — list all sessions
 * GET  /api/sessions/{id}/events  — SSE stream for real-time rotation progress
 */
@RestController
@RequestMapping("/api/sessions")
public class JitSessionApiController {

    private final SessionService sessionService;

    public JitSessionApiController(SessionService sessionService) {
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
