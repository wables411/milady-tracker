# One-click launcher for the Milady avatar tracker.
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path

# start the local server if it isn't already running
$listening = $false
try { $listening = [bool](Get-NetTCPConnection -LocalPort 8787 -State Listen -ErrorAction Stop) } catch {}
if (-not $listening) {
    Start-Process node -ArgumentList "`"$dir\serve.mjs`"" -WindowStyle Hidden -WorkingDirectory $dir
    Start-Sleep -Milliseconds 900
}

# open the avatar in its own app window (big-button mode, green screen on).
# The window gets its OWN browser profile whose permission store is pre-seeded
# with camera+mic grants for the tracker origin — the exact entries the
# browser writes when a user clicks Allow, so no prompts, no banners, and no
# test flags. The dedicated profile also forces a fresh browser process
# (windows joining an already-running browser ignore launch flags entirely).
$url = "http://127.0.0.1:8787/?bg=green"
$prof = Join-Path $env:LOCALAPPDATA 'MiladyTracker\profile'
$prefPath = Join-Path $prof 'Default\Preferences'
$needSeed = $true
if (Test-Path $prefPath) {
    if ([IO.File]::ReadAllText($prefPath).Contains('"http://127.0.0.1:8787,*"')) { $needSeed = $false }
}
if ($needSeed) {
    # stale profile from before the grants existed: rebuild it (loses only
    # this app window's saved toggles, one time)
    if (Test-Path $prof) { Remove-Item -Recurse -Force $prof }
    New-Item -ItemType Directory -Force (Split-Path $prefPath) | Out-Null
    [IO.File]::WriteAllText($prefPath,
        '{"profile":{"content_settings":{"exceptions":{' +
        '"media_stream_camera":{"http://127.0.0.1:8787,*":{"setting":1}},' +
        '"media_stream_mic":{"http://127.0.0.1:8787,*":{"setting":1}}}}}}')
}
$flags = @("--app=$url", "--user-data-dir=$prof",
           "--no-first-run", "--no-default-browser-check", "--hide-crash-restore-bubble")
$brave = "$env:ProgramFiles\BraveSoftware\Brave-Browser\Application\brave.exe"
if (Test-Path $brave) {
    Start-Process $brave -ArgumentList $flags
} else {
    try { Start-Process chrome -ArgumentList $flags }
    catch { try { Start-Process msedge -ArgumentList $flags } catch { Start-Process $url } }
}
