/*
 * Sample CyberArk Integration - C#/.NET
 * Used for testing ccp_code_scanner.py pattern detection.
 *
 * This file contains intentional CyberArk patterns that should be detected.
 */

// Pattern: DOTNET_CYBERARK_SDK - SDK imports
using CyberArk.AIM.PasswordManagement;
using CyberArk.PAS.SDK;

namespace SampleApp.Security
{
    public class CyberArkCredentialProvider
    {
        // Pattern: CCP_APPID
        private const string AppID = "DotNetWebApp";

        // Pattern: CCP_SAFE_REFERENCE
        private const string SafeName = "Application-Secrets";

        // Pattern: CCP_OBJECT_REFERENCE
        private const string ObjectName = "sql-service-account";

        // Pattern: CONFIG_CYBERARK_URL
        private readonly string _cyberarkUrl = "https://cyberark.company.com";
        private readonly string _aimUrl = "https://aim.company.com:18923";

        // Pattern: DOTNET_CYBERARK_SDK - PasswordSDK usage
        private readonly PasswordSDK _passwordSDK;

        public CyberArkCredentialProvider()
        {
            // Pattern: DOTNET_PASSWORD_REQUEST - SDK initialization
            _passwordSDK = new PasswordSDK();
        }

        /// <summary>
        /// Retrieve password using CyberArk .NET SDK
        /// </summary>
        public string GetPassword(string safe, string account)
        {
            // Pattern: DOTNET_PASSWORD_REQUEST - PasswordRequest
            var request = new PasswordRequest
            {
                AppID = AppID,
                Safe = safe,
                Object = account
            };

            // Pattern: DOTNET_PASSWORD_REQUEST - GetPassword call
            var response = _passwordSDK.GetPassword(request);

            // Pattern: DOTNET_PASSWORD_REQUEST - Password property access
            return response.Password;
        }

        /// <summary>
        /// Alternative: REST API call
        /// </summary>
        public async Task<string> GetPasswordViaRest()
        {
            using var client = new HttpClient();

            // Pattern: CCP_REST_ENDPOINT - AIMWebService
            var url = $"{_aimUrl}/AIMWebService/api/Accounts" +
                      $"?AppID={AppID}&Safe={SafeName}&Object={ObjectName}";

            var response = await client.GetAsync(url);
            var json = await response.Content.ReadAsStringAsync();

            // Parse and return password
            return JsonSerializer.Deserialize<CcpResponse>(json).Content;
        }

        /// <summary>
        /// Pattern: CONNECTION_STRING_CCP - CyberArk provider
        /// </summary>
        public string GetConnectionString()
        {
            // This connection string uses CyberArk credential provider
            return "Provider=CyberArk;Server=sqlserver.company.com;Database=AppDB;" +
                   "AppID=DotNetWebApp;Safe=Database-Creds;Object=sql-admin";
        }
    }

    // Pattern: DOTNET_PASSWORD_REQUEST - PSDKPasswordRequest class
    public class LegacyCredentialProvider
    {
        public string GetLegacyPassword()
        {
            var request = new PSDKPasswordRequest();
            request.AppID = "LegacyApp";
            request.Safe = "Legacy-Safe";
            request.Object = "legacy-account";

            return new PSDKPassword().GetPassword(request);
        }
    }
}
