package com.iopex.pamdx.controller.web;

import com.iopex.pamdx.service.PamService;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class SessionController {

    private final PamService pamService;

    public SessionController(PamService pamService) {
        this.pamService = pamService;
    }

    @GetMapping("/sessions")
    public String sessions(Model model) {
        model.addAttribute("vendor", pamService.getActiveVendor());
        model.addAttribute("activePage", "sessions");
        return "sessions";
    }
}
