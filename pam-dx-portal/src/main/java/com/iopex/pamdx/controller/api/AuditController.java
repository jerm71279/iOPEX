package com.iopex.pamdx.controller.api;

import com.iopex.pamdx.adapter.model.PamAuditEntry;
import com.iopex.pamdx.service.PamService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/audit")
@Tag(name = "Audit", description = "Retrieve PAM audit logs")
public class AuditController {

    private final PamService pamService;

    public AuditController(PamService pamService) {
        this.pamService = pamService;
    }

    @GetMapping
    @Operation(summary = "Get audit logs", description = "Retrieve audit entries for the last N days (default: 30)")
    public ResponseEntity<List<PamAuditEntry>> getAuditLogs(
            @RequestParam(defaultValue = "30") int days) {
        return ResponseEntity.ok(pamService.getAuditLogs(days));
    }
}
