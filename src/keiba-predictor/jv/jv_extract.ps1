# JV-Link extractor. Run with 32-bit PowerShell:
#   C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe -ExecutionPolicy Bypass -File jv_extract.ps1 -Spec RACE -From 20160101000000 -Option 4 -Keep RA,SE,HR,O1
# Writes raw JV-Data records (cp932, one record per line) to <OutDir>\<Spec>\<ID>_<YYYY>.txt
# ASCII only (PowerShell 5.1 reads BOM-less files as ANSI).
param(
  [string]$Spec = "RACE",
  [string]$From = "20160101000000",
  [int]$Option = 4,                      # 1=normal 3=setup(with dialog) 4=setup(no dialog)
  [string[]]$Keep = @("RA", "SE", "HR", "O1"),
  [string]$OutDir = "C:\keiba_db\jv_raw"
)
$ErrorActionPreference = "Stop"
$Keep = @($Keep | ForEach-Object { $_ -split "," } | Where-Object { $_ })   # -ArgumentList passes "RA,SE" as one string
if ([IntPtr]::Size -ne 4) { "ERROR: run with 32-bit PowerShell (SysWOW64)"; exit 2 }
$dir = Join-Path $OutDir $Spec
New-Item -ItemType Directory -Force $dir | Out-Null
$jv = New-Object -ComObject JVDTLab.JVLink
$r = $jv.JVInit("UNKNOWN"); "JVInit: $r"; if ($r -ne 0) { exit 1 }
$rc = 0; $dc = 0; $ts = ""
$r = $jv.JVOpen($Spec, $From, $Option, [ref]$rc, [ref]$dc, [ref]$ts)
"JVOpen: $r  readcount=$rc downloadcount=$dc lastfiletimestamp=$ts"
if ($r -lt 0) { $jv.JVClose() | Out-Null; exit 1 }
$enc = [System.Text.Encoding]::GetEncoding(932)
$writers = @{}; $counts = @{}; $files = 0; $skipped = 0; $n = 0; $t0 = Get-Date; $lastLog = Get-Date
try {
  while ($true) {
    $buff = ""; $size = 110000; $fname = ""
    $ret = $jv.JVRead([ref]$buff, [ref]$size, [ref]$fname)
    if ($ret -eq 0) { break }
    if ($ret -eq -1) { $files++; continue }
    if ($ret -eq -3) { Start-Sleep -Milliseconds 500; continue }      # still downloading
    if ($ret -lt 0) { "JVRead error: $ret file=$fname"; if ($ret -le -400) { $jv.JVSkip() | Out-Null; continue } else { break } }
    $id = $buff.Substring(0, 2)
    if ($Keep -notcontains $id) { $skipped++; continue }          # do not JVSkip: it skips the rest of the file
    $year = $buff.Substring(11, 4)
    $key = "${id}_$year"
    if (-not $writers.ContainsKey($key)) { $writers[$key] = New-Object System.IO.StreamWriter((Join-Path $dir "$key.txt"), $false, $enc); $counts[$key] = 0 }
    $writers[$key].Write($buff)
    $counts[$key]++; $n++
    if (((Get-Date) - $lastLog).TotalSeconds -ge 60) { "  {0:HH:mm} files={1}/{2} records={3} status={4}" -f (Get-Date), $files, $rc, $n, $jv.JVStatus(); $lastLog = Get-Date }
  }
} finally {
  foreach ($w in $writers.Values) { $w.Close() }
  $jv.JVClose() | Out-Null
}
"done: files=$files skippedFiles=$skipped records=$n elapsed={0:N0}s lastfiletimestamp=$ts" -f ((Get-Date) - $t0).TotalSeconds
$counts.GetEnumerator() | Sort-Object Name | ForEach-Object { "  {0}: {1}" -f $_.Name, $_.Value }
