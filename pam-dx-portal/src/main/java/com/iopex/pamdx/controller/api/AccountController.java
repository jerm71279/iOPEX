package com.iopex.pamdx.controller.api;

import com.iopex.pamdx.adapter.model.PamAccount;
import com.iopex.pamdx.service.PamService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/accounts")
@Tag(name = "Accounts", description = "Manage privileged accounts/secrets across any PAM vendor")
public class AccountController {

    private final PamService pamService;

    public AccountController(PamService pamService) {
        this.pamService = pamService;
    }

    @GetMapping
    @Operation(summary = "List accounts", description = "Paginated list of all privileged accounts. Filters are vendor-interpreted.")
    public ResponseEntity<List<PamAccount>> listAccounts(@RequestParam(required = false) Map<String, String> filters) {
        return ResponseEntity.ok(pamService.getAccounts(filters));
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get account details", description = "Full account details including properties and tags")
    public ResponseEntity<PamAccount> getAccount(@PathVariable String id) {
        return ResponseEntity.ok(pamService.getAccount(id));
    }

    @PostMapping("/{id}/retrieve")
    @Operation(summary = "Retrieve password", description = "Retrieve the secret value for an account. Audit logged.")
    public ResponseEntity<Map<String, String>> retrievePassword(
            @PathVariable String id,
            @RequestBody Map<String, String> body) {
        String reason = body.getOrDefault("reason", "Portal access");
        String password = pamService.retrievePassword(id, reason);
        return ResponseEntity.ok(Map.of("value", password));
    }
}
