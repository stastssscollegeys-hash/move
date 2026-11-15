param([string]$f)
Add-Type -AssemblyName System.Windows.Forms
$frag = [System.IO.File]::ReadAllText($f, [System.Text.Encoding]::UTF8)
$enc = New-Object System.Text.UTF8Encoding($false)
$pre = "<html><head><meta charset=""utf-8""></head><body><!--StartFragment-->"
$post = "<!--EndFragment--></body></html>"
$hdrT = "Version:0.9`r`nStartHTML:{0:D10}`r`nEndHTML:{1:D10}`r`nStartFragment:{2:D10}`r`nEndFragment:{3:D10}`r`n"
$hl = $enc.GetByteCount(($hdrT -f 0,0,0,0))
$sh = $hl; $sf = $sh + $enc.GetByteCount($pre); $ef = $sf + $enc.GetByteCount($frag); $eh = $ef + $enc.GetByteCount($post)
$all = ($hdrT -f $sh,$eh,$sf,$ef) + $pre + $frag + $post
$ms = New-Object System.IO.MemoryStream(,$enc.GetBytes($all))
$d = New-Object System.Windows.Forms.DataObject
$d.SetData("HTML Format", $ms)
$plain = [regex]::Replace($frag, "<[^>]+>", "")
$d.SetData([System.Windows.Forms.DataFormats]::UnicodeText, $plain)
[System.Windows.Forms.Clipboard]::SetDataObject($d, $true)
Write-Output ("html clip " + $frag.Length)
