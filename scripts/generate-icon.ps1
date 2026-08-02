param(
    [string]$OutputPath = (Join-Path (Split-Path -Parent $PSScriptRoot) "web\electron\icon.png")
)

Add-Type -AssemblyName System.Drawing

$dir = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $dir | Out-Null

$size = 512
$bmp = New-Object System.Drawing.Bitmap($size, $size)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.Clear([System.Drawing.Color]::Transparent)

function New-RoundedRectPath([float]$x, [float]$y, [float]$w, [float]$h, [float]$r) {
    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $d = $r * 2
    $path.AddArc($x, $y, $d, $d, 180, 90)
    $path.AddArc($x + $w - $d, $y, $d, $d, 270, 90)
    $path.AddArc($x + $w - $d, $y + $h - $d, $d, $d, 0, 90)
    $path.AddArc($x, $y + $h - $d, $d, $d, 90, 90)
    $path.CloseFigure()
    return $path
}

$bg = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 76, 175, 80))
$g.FillEllipse($bg, 16, 16, 480, 480)

$white = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
$mic = New-RoundedRectPath 216 120 80 200 40
$g.FillPath($white, $mic)
$g.FillRectangle($white, 246, 320, 20, 56)

$pen = New-Object System.Drawing.Pen ([System.Drawing.Color]::White, 16)
$g.DrawArc($pen, 176, 356, 160, 128, 180, 180)

$g.Dispose()
$bmp.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()

Write-Host "图标已生成: $OutputPath"
