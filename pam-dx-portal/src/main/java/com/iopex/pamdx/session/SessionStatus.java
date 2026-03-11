package com.iopex.pamdx.session;

public enum SessionStatus {
    ACTIVE,     // credential injected, session live
    ROTATING,   // session ended, rotation in progress
    ENDED,      // rotation complete, session closed
    EXPIRED     // timed out before explicit end
}
