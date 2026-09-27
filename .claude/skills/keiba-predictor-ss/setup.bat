@echo off
chcp 65001 > nul
echo ============================================
echo  keiba-predictor セットアップ (Windows)
echo ============================================
echo.

:: Python確認
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python が見つかりません。
    echo Python 3.10以上をインストールしてください。
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version') do set PYVER=%%v
echo [OK] Python %PYVER% を検出

:: 依存ライブラリインストール
echo.
echo [1/3] ライブラリをインストール中...
cd src\keiba-predictor
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] pip install に失敗しました
    pause
    exit /b 1
)
echo [OK] ライブラリのインストール完了
cd ..\..

:: keiba-index の依存も入れる
cd src\keiba-index
pip install -r requirements.txt -q
cd ..\..

:: .env ファイル作成
echo.
echo [2/3] 設定ファイルを確認中...
if not exist .env (
    copy .env.example .env > nul
    echo [OK] .env ファイルを作成しました
    echo     → .env を開いてAPIキーを設定してください
) else (
    echo [OK] .env は既に存在します（スキップ）
)

:: キャッシュディレクトリ作成
echo.
echo [3/3] キャッシュディレクトリを準備中...
if not exist src\keiba-predictor\_cache mkdir src\keiba-predictor\_cache
echo [OK] 完了

echo.
echo ============================================
echo  セットアップ完了！
echo ============================================
echo.
echo 次のステップ:
echo   1. .env を開いてAPIキーを設定 (X/noteへ投稿する場合)
echo   2. 予想を実行:
echo      cd src\keiba-predictor\scripts
echo      python predict_and_report.py --tomorrow
echo.
echo 詳細は README.md を確認してください。
echo.
pause
