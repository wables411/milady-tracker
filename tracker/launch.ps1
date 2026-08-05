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
# Permissions live per-browser — use the browser the user actually uses:
# Brave, then Chrome, then Edge, then whatever handles the URL.
$url = "http://127.0.0.1:8787/?bg=green"
$brave = "$env:ProgramFiles\BraveSoftware\Brave-Browser\Application\brave.exe"
if (Test-Path $brave) {
    Start-Process $brave -ArgumentList "--app=$url"
} else {
    try { Start-Process chrome -ArgumentList "--app=$url" }
    catch { try { Start-Process msedge -ArgumentList "--app=$url" } catch { Start-Process $url } }
}
