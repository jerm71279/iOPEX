package com.iopex.pamdx.config;

import com.iopex.pamdx.adapter.PamVendorAdapter;
import com.iopex.pamdx.adapter.cyberark.CyberArkAdapter;
import com.iopex.pamdx.adapter.delinea.DelineaAdapter;
import com.iopex.pamdx.adapter.strongdm.StrongDmAdapter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Registers the active PAM vendor adapter bean based on the
 * {@code pam.active-vendor} configuration property.
 *
 * <p>To switch vendors, change {@code pam.active-vendor} in application.yml
 * or set the {@code PAM_ACTIVE_VENDOR} environment variable.</p>
 */
@Configuration
public class AdapterConfig {

    private static final Logger log = LoggerFactory.getLogger(AdapterConfig.class);

    @Value("${pam.active-vendor:cyberark}")
    private String activeVendor;

    @Value("${pam.cyberark.base-url:}")
    private String cyberArkBaseUrl;

    @Value("${pam.cyberark.auth-type:cyberark}")
    private String cyberArkAuthType;

    @Value("${pam.delinea.base-url:}")
    private String delineaBaseUrl;

    @Value("${pam.strongdm.api-url:}")
    private String strongDmApiUrl;

    @Bean
    public PamVendorAdapter pamVendorAdapter() {
        log.info("Configuring PAM adapter for vendor: {}", activeVendor);

        return switch (activeVendor.toLowerCase()) {
            case "cyberark" -> new CyberArkAdapter(cyberArkBaseUrl, cyberArkAuthType);
            case "delinea" -> new DelineaAdapter(delineaBaseUrl);
            case "strongdm" -> new StrongDmAdapter(strongDmApiUrl);
            default -> throw new IllegalArgumentException(
                    "Unknown PAM vendor: " + activeVendor
                            + ". Supported: cyberark, delinea, strongdm");
        };
    }
}
