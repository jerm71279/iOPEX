package com.iopex.pamdx.controller.api;

import com.iopex.pamdx.adapter.model.PamHealthStatus;
import com.iopex.pamdx.service.PamService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/health")
@Tag(name = "Health", description = "PAM adapter connectivity and preflight checks")
public class HealthController {

    private final PamService pamService;

    public HealthController(PamService pamService) {
        this.pamService = pamService;
    }

    @GetMapping
    @Operation(summary = "Preflight check", description = "Run connectivity, auth, and permissions checks against the active PAM vendor")
    public ResponseEntity<PamHealthStatus> preflightCheck() {
        return ResponseEntity.ok(pamService.preflightCheck());
    }

    @GetMapping("/vendor")
    @Operation(summary = "Active vendor info")
    public ResponseEntity<Map<String, Object>> vendorInfo() {
        return ResponseEntity.ok(Map.of(
                "vendor", pamService.getActiveVendor(),
                "connected", pamService.isConnected()
        ));
    }
}
