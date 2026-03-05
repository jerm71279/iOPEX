package com.iopex.pamdx.controller;

import com.iopex.pamdx.adapter.PamVendorAdapter;
import com.iopex.pamdx.adapter.model.PamHealthStatus;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class AccountControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void healthEndpointIsPublic() throws Exception {
        mockMvc.perform(get("/api/v1/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.vendor").exists())
                .andExpect(jsonPath("$.connected").exists());
    }

    @Test
    void vendorEndpointIsPublic() throws Exception {
        mockMvc.perform(get("/api/v1/health/vendor"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.vendor").value("CyberArk"))
                .andExpect(jsonPath("$.connected").value(false));
    }

    @Test
    void accountsEndpointRequiresAuth() throws Exception {
        mockMvc.perform(get("/api/v1/accounts"))
                .andExpect(status().is3xxRedirection());
    }

    @Test
    @WithMockUser(roles = "ADMIN")
    void dashboardRendersForAuthenticatedUser() throws Exception {
        mockMvc.perform(get("/"))
                .andExpect(status().isOk())
                .andExpect(view().name("dashboard"));
    }
}
