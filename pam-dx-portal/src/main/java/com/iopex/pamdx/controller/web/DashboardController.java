package com.iopex.pamdx.controller.web;

import com.iopex.pamdx.adapter.model.PamHealthStatus;
import com.iopex.pamdx.service.PamService;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class DashboardController {

    private final PamService pamService;

    public DashboardController(PamService pamService) {
        this.pamService = pamService;
    }

    @GetMapping("/")
    public String dashboard(Model model) {
        model.addAttribute("vendor", pamService.getActiveVendor());
        model.addAttribute("connected", pamService.isConnected());
        model.addAttribute("activePage", "dashboard");

        PamHealthStatus health = pamService.preflightCheck();
        model.addAttribute("serverVersion", health.version());
        model.addAttribute("healthChecks", health.checks());
        model.addAttribute("healthPassed", health.checks().stream().filter(PamHealthStatus.CheckItem::passed).count());
        model.addAttribute("healthTotal", health.checks().size());

        return "dashboard";
    }

    @GetMapping("/login")
    public String login() {
        return "login";
    }
}
