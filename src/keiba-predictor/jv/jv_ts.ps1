# JV-Link time-series odds (0B41 win/place, 0B42 quinella) for many races in one session. 32-bit PowerShell. ASCII only.
param([string]$KeyFile, [string]$Spec = "0B41", [string]$OutDir = "C:\keiba_db\jv_raw\TS")
$ErrorActionPreference = "Continue"
if ([IntPtr]::Size -ne 4) { "ERROR: run with 32-bit PowerShell (SysWOW64)"; exit 2 }
New-Item -ItemType Directory -Force $OutDir | Out-Null
$jv = New-Object -ComObject JVDTLab.JVLink
$r = $jv.JVInit("UNKNOWN"); "JVInit: $r"
$enc = [System.Text.Encoding]::GetEncoding(932)
$n = 0
foreach ($key in Get-Content $KeyFile) {
  $key = $key.Trim(); if (-not $key) { continue }
  $out = Join-Path $OutDir "$key.txt"
  if (Test-Path $out) { continue }
  $r = $jv.JVRTOpen($Spec, $key)
  if ($r -lt 0) { "open error $r $key"; continue }
  $w = New-Object System.IO.StreamWriter($out, $false, $enc)
  while ($true) {
    $buff = ""; $size = 110000; $fname = ""
    $ret = $jv.JVRead([ref]$buff, [ref]$size, [ref]$fname)
    if ($ret -eq 0) { break }
    if ($ret -eq -1) { continue }
    if ($ret -eq -3) { Start-Sleep -Milliseconds 300; continue }
    if ($ret -lt 0) { "read error $ret $key"; break }
    $w.Write($buff)
  }
  $w.Close(); $jv.JVClose() | Out-Null
  $n++
  if ($n % 100 -eq 0) { "{0:HH:mm} {1} races" -f (Get-Date), $n }
}
"done $n"
