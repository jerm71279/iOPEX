package com.iopex.pamdx.controller.web;

import com.iopex.pamdx.service.PamService;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

import java.util.Map;

@Controller
public class SecretsController {

    private final PamService pamService;

    public SecretsController(PamService pamService) {
        this.pamService = pamService;
    }

    @GetMapping("/secrets")
    public String secrets(Model model) {
        model.addAttribute("vendor", pamService.getActiveVendor());
        model.addAttribute("activePage", "secrets");

        try {
            model.addAttribute("accounts", pamService.getAccounts(Map.of()));
        } catch (UnsupportedOperationException e) {
            model.addAttribute("accounts", null);
        }

        return "secrets";
    }
}
