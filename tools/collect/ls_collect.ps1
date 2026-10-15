$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$src  = Join-Path $env:USERPROFILE "Downloads\com.dmm.games.loststories\files\UnityCache\Shared"
$dst  = Join-Path $env:USERPROFILE "Downloads\ls_story"
$zip  = Join-Path $env:USERPROFILE "Downloads\ls_story.zip"
$list = Get-Content (Join-Path $here "ls_filelist.txt")
$i = 0; $miss = 0
foreach ($line in $list) {
  if (-not $line) { continue }
  $parts = $line -split '\|'
  $from = Join-Path $src $parts[0]
  $to   = Join-Path $dst $parts[1]
  $i++
  if (-not (Test-Path -LiteralPath $from)) { $miss++; continue }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $to) | Out-Null
  Copy-Item -LiteralPath $from -Destination $to -Force
  if ($i % 500 -eq 0) { Write-Host "$i / $($list.Count) copied" }
}
Write-Host "Copied $($i - $miss) files, missing $miss"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path (Join-Path $dst "*") -DestinationPath $zip
Write-Host "Done: $zip"
