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
        sessionService = new SessionService(new PamService(new DemoAdapter()));
    }

    @Test
    void startSessionCreatesActiveRecord() {
        var session = sessionService.startSession("user-alice", "demo-account-001", "test access");
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
    void maskedSecretContainsBullets() {
        var session = sessionService.startSession("user-bob", "demo-account-002", "test");
        assertTrue(session.maskedSecret().contains("••"), "Secret should be partially masked");
    }

    @Test
    void getSessionReturnsActiveSession() {
        var started = sessionService.startSession("user-carol", "demo-account-003", "test");
        var retrieved = sessionService.getSession(started.sessionId());
        assertEquals(started.sessionId(), retrieved.sessionId());
    }

    @Test
    void getSessionThrowsForUnknownId() {
        assertThrows(IllegalArgumentException.class,
            () -> sessionService.getSession("nonexistent-id"));
    }

    @Test
    void endSessionTriggersRotation() throws InterruptedException {
        var started = sessionService.startSession("user-dan", "demo-account-004", "test");
        sessionService.endSession(started.sessionId());

        // Wait for async rotation (4 steps × ~800ms + buffer)
        Thread.sleep(5000);

        var ended = sessionService.getSession(started.sessionId());
        assertEquals(SessionStatus.ENDED, ended.status());
        assertTrue(ended.rotationTriggered());
        assertNotNull(ended.endedAt());
        assertNotNull(ended.rotationNewMasked());
    }
}
