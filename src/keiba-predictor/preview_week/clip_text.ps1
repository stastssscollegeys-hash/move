param([string]$f)
$t = [System.IO.File]::ReadAllText($f, [System.Text.Encoding]::UTF8)
Set-Clipboard -Value $t
Write-Output ("clip " + $t.Length)
