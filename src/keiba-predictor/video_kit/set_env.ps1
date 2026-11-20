# このPCで video_kit の Python の道具を使う前に、PowerShell で1回読み込む:  . .\src\keiba-predictor\video_kit\set_env.ps1
# （秘密情報は入れない。APIキーはリポジトリ直下の .env）
$env:KVC_WORK_ROOT  = "C:/Users/User/Desktop/競馬予想レポート"
$env:KVC_CHAR_SHEET = "C:/Users/User/Downloads/アスメシキャラクターシート文字なし.png"
$env:KVC_BGM_DIR    = "C:/Users/User/Desktop/効果音素材（動画用）/youtube audio v2"
$env:KVC_SE_DIR     = "C:/Users/User/Desktop/効果音素材（動画用）/youtube audio"
$env:PYTHONIOENCODING = "utf-8"
Write-Host "video_kit の置き場所を設定しました（$env:KVC_WORK_ROOT）"
