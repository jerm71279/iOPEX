package com.iopex.pamdx.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Spring Security configuration.
 *
 * <p>Development mode: form login with in-memory users.
 * Production: replace with OAuth2/OIDC provider (Okta, Azure AD, CyberArk Identity).</p>
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/v1/health", "/api/v1/health/**").permitAll()
                .requestMatchers("/swagger-ui/**", "/v3/api-docs/**").permitAll()
                .requestMatchers("/css/**", "/js/**", "/images/**").permitAll()
                .requestMatchers("/actuator/health").permitAll()
                .requestMatchers("/session-demo.html").permitAll()
                .requestMatchers("/api/sessions/**").permitAll()
                .anyRequest().authenticated()
            )
            .formLogin(form -> form
                .loginPage("/login")
                .defaultSuccessUrl("/", true)
                .permitAll()
            )
            .logout(logout -> logout
                .logoutSuccessUrl("/login?logout")
                .permitAll()
            )
            .csrf(csrf -> csrf
                .ignoringRequestMatchers("/api/**")
            );

        return http.build();
    }

    @Bean
    @SuppressWarnings("deprecation")
    public UserDetailsService userDetailsService() {
        // Development only — replace with OIDC/LDAP in production
        var admin = User.withDefaultPasswordEncoder()
                .username("admin")
                .password("admin")
                .roles("ADMIN", "PAM_OPERATOR")
                .build();

        var viewer = User.withDefaultPasswordEncoder()
                .username("viewer")
                .password("viewer")
                .roles("PAM_VIEWER")
                .build();

        return new InMemoryUserDetailsManager(admin, viewer);
    }
}
