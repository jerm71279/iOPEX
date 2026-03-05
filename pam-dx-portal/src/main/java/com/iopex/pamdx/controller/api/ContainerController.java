package com.iopex.pamdx.controller.api;

import com.iopex.pamdx.adapter.model.PamContainer;
import com.iopex.pamdx.service.PamService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/containers")
@Tag(name = "Containers", description = "Manage PAM containers (CyberArk Safes / SS Folders / StrongDM Resource Groups)")
public class ContainerController {

    private final PamService pamService;

    public ContainerController(PamService pamService) {
        this.pamService = pamService;
    }

    @GetMapping
    @Operation(summary = "List containers")
    public ResponseEntity<List<PamContainer>> listContainers() {
        return ResponseEntity.ok(pamService.getContainers());
    }

    @PostMapping
    @Operation(summary = "Create container")
    public ResponseEntity<PamContainer> createContainer(@RequestBody Map<String, Object> body) {
        String name = (String) body.get("name");
        return ResponseEntity.ok(pamService.createContainer(name, body));
    }
}
