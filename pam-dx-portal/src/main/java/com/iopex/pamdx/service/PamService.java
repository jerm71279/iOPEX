package com.iopex.pamdx.service;

import com.iopex.pamdx.adapter.PamVendorAdapter;
import com.iopex.pamdx.adapter.model.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

/**
 * Business logic layer between controllers and the active PAM vendor adapter.
 * All portal and API operations route through this service.
 */
@Service
public class PamService {

    private static final Logger log = LoggerFactory.getLogger(PamService.class);
    private final PamVendorAdapter adapter;

    public PamService(PamVendorAdapter adapter) {
        this.adapter = adapter;
        log.info("PamService initialized with vendor: {}", adapter.getVendorName());
    }

    public String getActiveVendor() {
        return adapter.getVendorName();
    }

    public boolean isConnected() {
        return adapter.isConnected();
    }

    public boolean connect() {
        log.info("Connecting to {} PAM...", adapter.getVendorName());
        return adapter.connect();
    }

    public List<PamAccount> getAccounts(Map<String, String> filters) {
        return adapter.getAccounts(filters != null ? filters : Map.of());
    }

    public PamAccount getAccount(String accountId) {
        return adapter.getAccount(accountId);
    }

    public String retrievePassword(String accountId, String reason) {
        log.info("Password retrieval requested for account {} — reason: {}", accountId, reason);
        return adapter.retrievePassword(accountId, reason);
    }

    public List<PamContainer> getContainers() {
        return adapter.getContainers();
    }

    public PamContainer createContainer(String name, Map<String, Object> properties) {
        log.info("Creating container: {}", name);
        return adapter.createContainer(name, properties);
    }

    public List<PamPlatform> getPlatforms() {
        return adapter.getPlatforms();
    }

    public List<PamAuditEntry> getAuditLogs(int days) {
        return adapter.getAuditLogs(days);
    }

    public PamHealthStatus preflightCheck() {
        return adapter.preflightCheck();
    }
}
