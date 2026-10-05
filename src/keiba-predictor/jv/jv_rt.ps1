# JV-Link realtime reader (0B12 results, 0B15 payouts). 32-bit PowerShell. ASCII only.
param([string]$Spec = "0B12", [string]$Key = "20261003", [string]$OutDir = "C:\keiba_db\jv_raw\RT")
$ErrorActionPreference = "Stop"
if ([IntPtr]::Size -ne 4) { "ERROR: run with 32-bit PowerShell (SysWOW64)"; exit 2 }
New-Item -ItemType Directory -Force $OutDir | Out-Null
$jv = New-Object -ComObject JVDTLab.JVLink
$r = $jv.JVInit("UNKNOWN"); "JVInit: $r"
$rc = 0
$r = $jv.JVRTOpen($Spec, $Key); "JVRTOpen: $r"
if ($r -lt 0) { exit 1 }
$enc = [System.Text.Encoding]::GetEncoding(932)
$w = @{}; $n = 0
while ($true) {
  $buff = ""; $size = 110000; $fname = ""
  $ret = $jv.JVRead([ref]$buff, [ref]$size, [ref]$fname)
  if ($ret -eq 0) { break }
  if ($ret -eq -1) { continue }
  if ($ret -eq -3) { Start-Sleep -Milliseconds 500; continue }
  if ($ret -lt 0) { "JVRead error: $ret"; break }
  $id = $buff.Substring(0, 2)
  $k = "${id}_$Key"
  if (-not $w.ContainsKey($k)) { $w[$k] = New-Object System.IO.StreamWriter((Join-Path $OutDir "$k.txt"), $false, $enc) }
  $w[$k].Write($buff); $n++
}
foreach ($x in $w.Values) { $x.Close() }
$jv.JVClose() | Out-Null
"done records=$n"
$w.Keys | Sort-Object | ForEach-Object { $_ }
