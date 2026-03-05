package com.iopex.pamdx.controller.api;

import com.iopex.pamdx.adapter.model.PamPlatform;
import com.iopex.pamdx.service.PamService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/platforms")
@Tag(name = "Platforms", description = "List PAM platforms (CyberArk Platforms / SS Templates / StrongDM Policies)")
public class PlatformController {

    private final PamService pamService;

    public PlatformController(PamService pamService) {
        this.pamService = pamService;
    }

    @GetMapping
    @Operation(summary = "List platforms/templates")
    public ResponseEntity<List<PamPlatform>> listPlatforms() {
        return ResponseEntity.ok(pamService.getPlatforms());
    }
}
