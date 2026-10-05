# JV-Link probe (run with 32-bit PowerShell: C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe)
# ASCII only. Reads a small recent slice and dumps the first records of each type as cp932 text.
param([string]$Spec = "RACE", [string]$From = "20260920000000", [int]$Option = 1, [string]$OutDir = "$PSScriptRoot\probe")
$ErrorActionPreference = "Stop"
"bitness: " + ([IntPtr]::Size * 8)
New-Item -ItemType Directory -Force $OutDir | Out-Null
$jv = New-Object -ComObject JVDTLab.JVLink
$r = $jv.JVInit("UNKNOWN"); "JVInit: $r"
$rc = 0; $dc = 0; $ts = ""
$r = $jv.JVOpen($Spec, $From, $Option, [ref]$rc, [ref]$dc, [ref]$ts)
"JVOpen: $r  readcount=$rc downloadcount=$dc lastfiletimestamp=$ts"
if ($r -lt 0) { $jv.JVClose() | Out-Null; exit 1 }
$t0 = Get-Date
while ($dc -gt 0) { $st = $jv.JVStatus(); if ($st -ge $dc -or $st -lt 0) { "JVStatus: $st"; break }; Start-Sleep -Milliseconds 500; if (((Get-Date) - $t0).TotalSeconds -gt 600) { "download timeout"; break } }
$enc = [System.Text.Encoding]::GetEncoding(932)
$counts = @{}; $files = 0; $n = 0
$writers = @{}
while ($true) {
  $buff = ""; $size = 110000; $fname = ""
  $ret = $jv.JVRead([ref]$buff, [ref]$size, [ref]$fname)
  if ($ret -eq 0) { break }
  if ($ret -eq -1) { $files++; continue }
  if ($ret -eq -3) { Start-Sleep -Milliseconds 300; continue }
  if ($ret -lt 0) { "JVRead error: $ret ($fname)"; break }
  $id = $buff.Substring(0, 2)
  if (-not $counts.ContainsKey($id)) { $counts[$id] = 0; $writers[$id] = New-Object System.IO.StreamWriter("$OutDir\$id.txt", $false, $enc) }
  $counts[$id]++
  if ($counts[$id] -le 60) { $writers[$id].Write($buff) }
  $n++
}
foreach ($w in $writers.Values) { $w.Close() }
$jv.JVClose() | Out-Null
"files=$files records=$n"
$counts.GetEnumerator() | Sort-Object Name | ForEach-Object { "  {0}: {1}" -f $_.Name, $_.Value }
