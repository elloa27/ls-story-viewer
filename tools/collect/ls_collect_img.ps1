$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$src  = Join-Path $env:USERPROFILE "Downloads\com.dmm.games.loststories\files\UnityCache\Shared"
$base = Join-Path $env:USERPROFILE "Downloads\ls_img"
$list = Get-Content (Join-Path $here "ls_img_list.txt") | Where-Object { $_ }
$parts = $list | ForEach-Object { ($_ -split '\|')[0] } | Sort-Object { [int]$_ } -Unique
$miss = 0
foreach ($p in $parts) {
  $dir = Join-Path $base ("part" + $p)
  $zip = Join-Path $env:USERPROFILE ("Downloads\ls_img_part" + $p + ".zip")
  if (Test-Path $zip) { Write-Host "part$p 이미 있음 - 건너뜀"; continue }
  Write-Host "part$p 복사 중..."
  foreach ($line in ($list | Where-Object { $_.StartsWith("$p|") })) {
    $f = $line -split '\|'
    $from = Join-Path $src $f[1]; $to = Join-Path $dir $f[2]
    if (-not (Test-Path -LiteralPath $from)) { $miss++; continue }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $to) | Out-Null
    Copy-Item -LiteralPath $from -Destination $to -Force
  }
  Write-Host "part$p 압축 중..."
  Compress-Archive -Path (Join-Path $dir "*") -DestinationPath $zip -CompressionLevel NoCompression
  Remove-Item -Recurse -Force $dir
  Write-Host "  -> $zip"
}
Write-Host "완료. 없는 파일 $miss 개"
