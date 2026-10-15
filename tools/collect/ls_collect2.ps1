$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$src  = Join-Path $env:USERPROFILE "Downloads\com.dmm.games.loststories\files"
$base = Join-Path $env:USERPROFILE "Downloads\ls_c2"
$list = Get-Content (Join-Path $here "ls_list2.txt") | Where-Object { $_ }
$parts = $list | ForEach-Object { ($_ -split '\|')[0] } | Sort-Object { [int]$_ } -Unique
$miss = 0
foreach ($p in $parts) {
  $dir = Join-Path $base ("part" + $p)
  $zip = Join-Path $env:USERPROFILE ("Downloads\ls_c2_part" + $p + ".zip")
  if (Test-Path $zip) { Write-Host "part$p already exists - skip"; continue }
  Write-Host "part$p copying..."
  foreach ($line in ($list | Where-Object { $_.StartsWith("$p|") })) {
    $f = $line -split '\|'
    $from = Join-Path $src $f[1]; $to = Join-Path $dir $f[2]
    if (-not (Test-Path -LiteralPath $from)) { $miss++; continue }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $to) | Out-Null
    Copy-Item -LiteralPath $from -Destination $to -Force
  }
  Write-Host "part$p zipping..."
  Compress-Archive -Path (Join-Path $dir "*") -DestinationPath $zip -CompressionLevel NoCompression
  Remove-Item -Recurse -Force $dir
  Write-Host "  -> $zip"
}
Remove-Item -Recurse -Force $base -ErrorAction SilentlyContinue
Write-Host "DONE. missing files: $miss"
