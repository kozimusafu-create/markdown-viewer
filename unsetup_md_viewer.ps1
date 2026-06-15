# md_viewer 登録解除
# setup_md_viewer.ps1 で行った変更を元に戻す

$progId   = "MdViewer.MarkdownFile"
$classRoot = "HKCU:\Software\Classes"

Write-Host "=== md_viewer 登録解除 ===" -ForegroundColor Cyan

# .md のデフォルトを元に戻す（空にする）
$mdKey = "$classRoot\.md"
if (Test-Path $mdKey) {
    $cur = (Get-ItemProperty -Path $mdKey -Name "(Default)" -ErrorAction SilentlyContinue)."(Default)"
    if ($cur -eq $progId) {
        Set-ItemProperty -Path $mdKey -Name "(Default)" -Value ""
        Write-Host ".md のデフォルト関連付けを解除した"
    }
}

# OpenWithProgids から削除
$owKey = "$classRoot\.md\OpenWithProgids\$progId"
if (Test-Path $owKey) {
    Remove-Item -Path $owKey -Force
    Write-Host "OpenWithProgids から削除した"
}

# ProgID ごと削除
$pidKey = "$classRoot\$progId"
if (Test-Path $pidKey) {
    Remove-Item -Path $pidKey -Recurse -Force
    Write-Host "ProgID $progId を削除した"
}

if (-not ("Win32.NativeMethods" -as [type])) {
    Add-Type -Namespace Win32 -Name NativeMethods -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("shell32.dll")]
public static extern void SHChangeNotify(int wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);
'@
}
[Win32.NativeMethods]::SHChangeNotify(0x8000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)

Write-Host ""
Write-Host "完了。登録解除した。" -ForegroundColor Green
