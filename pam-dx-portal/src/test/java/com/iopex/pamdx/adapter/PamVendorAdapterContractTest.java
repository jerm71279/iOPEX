package com.iopex.pamdx.adapter;

import com.iopex.pamdx.adapter.cyberark.CyberArkAdapter;
import com.iopex.pamdx.adapter.delinea.DelineaAdapter;
import com.iopex.pamdx.adapter.strongdm.StrongDmAdapter;
import com.iopex.pamdx.adapter.demo.DemoAdapter;
import com.iopex.pamdx.adapter.model.PamHealthStatus;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Contract tests verifying all PamVendorAdapter implementations
 * provide the expected vendor identity and health check structure.
 */
class PamVendorAdapterContractTest {

    @Test
    void cyberArkAdapterReturnsCorrectVendorName() {
        PamVendorAdapter adapter = new CyberArkAdapter("https://pvwa.test.com/PasswordVault/api", "cyberark");
        assertEquals("CyberArk", adapter.getVendorName());
        assertFalse(adapter.isConnected());
    }

    @Test
    void delineaAdapterReturnsCorrectVendorName() {
        PamVendorAdapter adapter = new DelineaAdapter("https://ss.test.com/SecretServer");
        assertEquals("Delinea", adapter.getVendorName());
        assertFalse(adapter.isConnected());
    }

    @Test
    void strongDmAdapterReturnsCorrectVendorName() {
        PamVendorAdapter adapter = new StrongDmAdapter("https://app.strongdm.com");
        assertEquals("StrongDM", adapter.getVendorName());
        assertFalse(adapter.isConnected());
    }

    @Test
    void preflightCheckReturnsStructuredResult() {
        PamVendorAdapter adapter = new CyberArkAdapter("https://pvwa.test.com/PasswordVault/api", "cyberark");
        PamHealthStatus health = adapter.preflightCheck();

        assertNotNull(health);
        assertEquals("CyberArk", health.vendor());
        assertFalse(health.connected());
        assertNotNull(health.checkedAt());
        assertFalse(health.checks().isEmpty());
    }

    @Test
    void allAdaptersImplementSameInterface() {
        PamVendorAdapter[] adapters = {
                new CyberArkAdapter("https://pvwa.test.com/PasswordVault/api", "cyberark"),
                new DelineaAdapter("https://ss.test.com/SecretServer"),
                new StrongDmAdapter("https://app.strongdm.com")
        };

        for (PamVendorAdapter adapter : adapters) {
            assertNotNull(adapter.getVendorName(), "Vendor name should not be null for " + adapter.getClass().getSimpleName());
            assertFalse(adapter.isConnected(), "Should not be connected without calling connect()");

            PamHealthStatus health = adapter.preflightCheck();
            assertNotNull(health, "Preflight check should return a result for " + adapter.getVendorName());
        }
    }

    @Test
    void demoAdapterReturnsCorrectVendorName() {
        PamVendorAdapter adapter = new DemoAdapter();
        assertEquals("Demo", adapter.getVendorName());
        assertTrue(adapter.isConnected()); // always connected
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
}
