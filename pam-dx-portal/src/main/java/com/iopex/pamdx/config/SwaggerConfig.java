package com.iopex.pamdx.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.servers.Server;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;

/**
 * OpenAPI 3.0 / Swagger UI configuration.
 * Access at: /swagger-ui.html
 */
@Configuration
public class SwaggerConfig {

    @Bean
    public OpenAPI pamDxOpenApi() {
        return new OpenAPI()
                .info(new Info()
                        .title("PAM DX Portal API")
                        .version("1.0.0")
                        .description("""
                                Vendor-agnostic PAM Digital Experience API Gateway.

                                Provides a unified REST API for managing privileged accounts,
                                containers (safes/folders), platforms (templates), and audit logs
                                across any PAM vendor (CyberArk, Delinea, StrongDM, etc.).

                                The active vendor is configured via `pam.active-vendor` in application.yml.
                                """)
                        .contact(new Contact()
                                .name("iOPEX PAM Migration Team")
                                .email("pam-migration@iopex.com")))
                .servers(List.of(
                        new Server().url("/").description("Local")
                ));
    }
}
