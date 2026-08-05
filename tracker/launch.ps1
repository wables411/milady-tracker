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
# The window gets its OWN browser profile with media prompts auto-granted:
# --use-fake-ui-for-media-stream skips the permission prompt but uses the
# REAL camera and mic. The dedicated profile matters twice over — it keeps
# the grant away from normal browsing, and it forces a fresh browser process
# (windows joining an already-running browser ignore launch flags entirely).
$url = "http://127.0.0.1:8787/?bg=green"
$prof = Join-Path $env:LOCALAPPDATA 'MiladyTracker\profile'
$flags = @("--app=$url", "--user-data-dir=$prof", "--use-fake-ui-for-media-stream",
           "--no-first-run", "--no-default-browser-check", "--hide-crash-restore-bubble")
$brave = "$env:ProgramFiles\BraveSoftware\Brave-Browser\Application\brave.exe"
if (Test-Path $brave) {
    Start-Process $brave -ArgumentList $flags
} else {
    try { Start-Process chrome -ArgumentList $flags }
    catch { try { Start-Process msedge -ArgumentList $flags } catch { Start-Process $url } }
}
