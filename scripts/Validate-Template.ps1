param([switch]$RequirePersonalized)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$kvp = Get-Content -Raw (Join-Path $root 'bo3-t7x.kvp')
$keys = @{}
foreach ($line in ($kvp -split '\r?\n')) {
    if (!$line.Trim()) { continue }
    $pair = $line -split '=', 2
    if ($pair.Count -ne 2 -or $keys.ContainsKey($pair[0])) { throw "Invalid or duplicate KVP: $line" }
    $keys[$pair[0]] = $pair[1]
}
foreach ($name in @('manifest.json','bo3-t7xconfig.json','bo3-t7xports.json','bo3-t7xupdates.json')) {
    $null = Get-Content -Raw (Join-Path $root $name) | ConvertFrom-Json
}
foreach ($match in [regex]::Matches($kvp, '@IncludeJson\[([^\]]+)\]')) {
    if (!(Test-Path (Join-Path $root $match.Groups[1].Value))) { throw 'Missing include' }
}
$manifest = Get-Content -Raw (Join-Path $root 'manifest.json') | ConvertFrom-Json
$null = [guid]::Parse($manifest.id)
$null = [guid]::Parse($keys['Meta.AppConfigId'])
$settings = Get-Content -Raw (Join-Path $root 'bo3-t7xconfig.json') | ConvertFrom-Json
$defaults = $keys['App.AppSettings'] | ConvertFrom-Json
foreach ($setting in $settings) {
    if ($defaults.($setting.FieldName) -ne $setting.DefaultValue) { throw "Default mismatch: $($setting.FieldName)" }
}
$updates = Get-Content -Raw (Join-Path $root 'bo3-t7xupdates.json') | ConvertFrom-Json
foreach ($stage in $updates) {
    if ($stage.SkipOnFailure) { throw "Required stage may silently fail: $($stage.UpdateStageName)" }
    if ($stage.UpdateSource -eq 'FetchURL' -and !$stage.UpdateSourceArgs) { throw 'Missing download filename' }
}
if ($RequirePersonalized -and (($manifest | ConvertTo-Json) + $kvp) -match 'DEIN_GITHUB_NAME|DEIN_NAME') {
    throw 'Run scripts/Prepare-Repository.ps1 with your GitHub username first.'
}
Write-Host 'PASS: JSON, KVP, includes, IDs, defaults and update checks. AMP runtime not tested.'
