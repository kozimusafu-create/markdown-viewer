# markdown-viewer セットアップ
# .md ファイルを markdown-viewer で開けるよう Windows に登録する。
# 管理者権限不要（HKCU = 自分のアカウントのみ）。
#
# このスクリプトと同じフォルダにある md_viewer.exe（または md_viewer.py）を
# 自動検出して登録する。パスのハードコードなし。

$ErrorActionPreference = "Stop"
$here   = $PSScriptRoot
$progId = "MdViewer.MarkdownFile"

Write-Host "=== markdown-viewer セットアップ ===" -ForegroundColor Cyan

# 1) 起動コマンドを決定（exe 優先、なければ pythonw + .py）
$exe = Join-Path $here "md_viewer.exe"
$py  = Join-Path $here "md_viewer.py"

if (Test-Path $exe) {
    $command  = "`"$exe`" `"%1`""
    $iconPath = "$exe,0"
    Write-Host "起動方式 : exe ($exe)"
}
elseif (Test-Path $py) {
    $pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue)?.Source
    if (-not $pythonw) {
        Write-Host "pythonw.exe が見つからない。Python をインストールするか、md_viewer.exe を使うこと。" -ForegroundColor Red
        exit 1
    }
    $command  = "`"$pythonw`" `"$py`" `"%1`""
    $iconPath = "$pythonw,0"
    Write-Host "起動方式 : python ($pythonw)"
    Write-Host "          スクリプト: $py"
}
else {
    Write-Host "md_viewer.exe も md_viewer.py も見つからない。このスクリプトと同じフォルダに置くこと。" -ForegroundColor Red
    exit 1
}

# 2) ProgID 登録
$classRoot = "HKCU:\Software\Classes"
New-Item -Path "$classRoot\$progId"                            -Force | Out-Null
Set-ItemProperty -Path "$classRoot\$progId"                    -Name "(Default)" -Value "Markdown File"
New-Item -Path "$classRoot\$progId\shell\open\command"         -Force | Out-Null
Set-ItemProperty -Path "$classRoot\$progId\shell\open\command" -Name "(Default)" -Value $command
New-Item -Path "$classRoot\$progId\DefaultIcon"               -Force | Out-Null
Set-ItemProperty -Path "$classRoot\$progId\DefaultIcon"       -Name "(Default)" -Value $iconPath

# 3) .md 拡張子の Open With リストに追加
New-Item -Path "$classRoot\.md\OpenWithProgids"             -Force | Out-Null
New-Item -Path "$classRoot\.md\OpenWithProgids\$progId"     -Force | Out-Null

# 4) Explorer に変更通知
if (-not ("Win32.NativeMethods" -as [type])) {
    Add-Type -Namespace Win32 -Name NativeMethods -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("shell32.dll")]
public static extern void SHChangeNotify(int wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);
'@
}
[Win32.NativeMethods]::SHChangeNotify(0x8000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)

Write-Host ""
Write-Host "登録完了。" -ForegroundColor Green
Write-Host ""
Write-Host "【重要】Windows 10/11 は既定アプリの変更に手動確認が必要:" -ForegroundColor Yellow
Write-Host "  .md ファイルを右クリック → プログラムから開く → 別のプログラムを選択"
Write-Host "  → markdown-viewer を選び『常にこのアプリを使う』にチェック"
Write-Host ""
Write-Host "元に戻す場合は unsetup_md_viewer.ps1 を実行。" -ForegroundColor Yellow
