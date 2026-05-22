$ErrorActionPreference = "Stop"

$token = Read-Host "Enter GitHub PAT" -AsSecureString
$plainToken = [Runtime.InteropServices.Marshal]::PtrToStringUni(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($token)
)

if ([string]::IsNullOrWhiteSpace($plainToken)) {
    Write-Host "Token is empty. Nothing was saved."
    exit 1
}

[Environment]::SetEnvironmentVariable("GITHUB_TOKEN", $plainToken.Trim(), "User")
$env:GITHUB_TOKEN = $plainToken.Trim()

Write-Host "GITHUB_TOKEN saved to User environment variables."
Write-Host "Open a new terminal to use it automatically."
