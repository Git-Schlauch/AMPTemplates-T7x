param(
    [Parameter(Mandatory)][ValidatePattern('^[A-Za-z0-9][A-Za-z0-9-]{0,38}$')][string]$GitHubUser,
    [ValidatePattern('^[A-Za-z0-9_.-]+$')][string]$Repository = 'AMPTemplates-T7x'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$utf8 = New-Object System.Text.UTF8Encoding($false)
$manifestPath = Join-Path $root 'manifest.json'
$manifest = Get-Content -Raw $manifestPath | ConvertFrom-Json
$manifest.authors = @($GitHubUser)
$manifest.origin = "https://github.com/$GitHubUser/$Repository.git"
$manifest.url = "https://github.com/$GitHubUser/$Repository"
$manifest.prefix = 'T7X-' + $GitHubUser
[IO.File]::WriteAllText($manifestPath, (($manifest | ConvertTo-Json -Depth 5) + "`n").Replace("`r`n", "`n"), $utf8)
$templatePath = Join-Path $root 'bo3-t7x.kvp'
$template = Get-Content -Raw $templatePath
$template = [regex]::Replace($template, '(?m)^Meta.Author=.*$', "Meta.Author=$GitHubUser")
[IO.File]::WriteAllText($templatePath, $template.Replace("`r`n", "`n"), $utf8)
& (Join-Path $PSScriptRoot 'Validate-Template.ps1') -RequirePersonalized
Write-Host "AMP repository: ${GitHubUser}/${Repository}:main"
Write-Host 'Files prepared. No commit, upload or remote change was made.'
