# 工作区回归测试：更新工具链后跑一遍，全绿才说明环境正常。
# 用法（PowerShell）：powershell -ExecutionPolicy Bypass -File D:\E\项目\tools\regression_test.ps1
# 可选参数：-SkipKt（跳过带孔板，省 10-30 秒）、-SkipFatigue
param(
    [switch]$SkipKt,
    [switch]$SkipFatigue
)

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$env:PYTHONIOENCODING = 'utf-8'

$Root = 'D:\E\项目'
$Py   = 'F:\Python3.13.13\python.exe'
$Ccx  = Join-Path $Root 'tools\PrePoMax\Solver\ccx_dynamic.exe'
$Gmsh = 'F:\FreeCAD\bin\gmsh.exe'
$Work = Join-Path $Root 'tools\测试\regression'

$script:pass = 0
$script:fail = 0
$script:skip = 0

function Result {
    param([string]$Name, [bool]$Ok, [string]$Detail)
    if ($Ok) {
        $script:pass++
        Write-Host ('[PASS] ' + $Name + '  ' + $Detail) -ForegroundColor Green
    } else {
        $script:fail++
        Write-Host ('[FAIL] ' + $Name + '  ' + $Detail) -ForegroundColor Red
    }
}

function SkipStep {
    param([string]$Name, [string]$Why)
    $script:skip++
    Write-Host ('[SKIP] ' + $Name + '  ' + $Why) -ForegroundColor Yellow
}

function Invoke-Tool {
    param([string]$Exe, [string[]]$Arguments, [string]$WorkDir)
    Push-Location $WorkDir
    try {
        $out = & $Exe @Arguments 2>&1 | Out-String
        $code = $LASTEXITCODE
        if ($null -eq $code) { $code = 0 }
        return [pscustomobject]@{ Output = $out; Exit = $code }
    } finally {
        Pop-Location
    }
}

Write-Host '===== 建模 + FEA 工作区回归测试 =====' -ForegroundColor Cyan
Write-Host ('时间：' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
New-Item -ItemType Directory -Force -Path $Work | Out-Null

# ---------- 1. CalculiX 版本 ----------
if (Test-Path $Ccx) {
    $r = Invoke-Tool $Ccx @('-v') $Work
    $ver = ''
    if ($r.Output -match 'Version\s+([\d.]+)') { $ver = $Matches[1] }
    Result 'CalculiX 可执行' ($r.Output -match '2\.23') ('版本=' + $ver)
} else {
    Result 'CalculiX 可执行' $false ('找不到 ' + $Ccx)
}

# ---------- 2. 立方体单单元（SZZ 基线 122.496 / 77.4961） ----------
$cubeSrc = Join-Path $Root 'tools\测试\cube_tension.inp'
$cubeDir = Join-Path $Work 'cube'
New-Item -ItemType Directory -Force -Path $cubeDir | Out-Null
Copy-Item $cubeSrc (Join-Path $cubeDir 'cube.inp') -Force
Get-ChildItem $cubeDir -File | Where-Object { $_.Name -ne 'cube.inp' } | Remove-Item -Force -ErrorAction SilentlyContinue
$r = Invoke-Tool $Ccx @('-i', 'cube') $cubeDir
$cubeFrd = Join-Path $cubeDir 'cube.frd'
$ok = $false
$detail = 'exit=' + $r.Exit
if (Test-Path $cubeFrd) {
    $txt = Get-Content $cubeFrd -Raw
    $top = ($txt -match '1\.22496E\+02')
    $bot = ($txt -match '7\.74961E\+01')
    $ok = $top -and $bot
    $detail = 'SZZ 上=' + $top + ' 下=' + $bot
} else {
    $detail = '没有生成 cube.frd；exit=' + $r.Exit
}
Result '立方体基准算例' $ok $detail

# ---------- 3. 带孔板 Kt（基线 2.42–2.44） ----------
if ($SkipKt) {
    SkipStep '带孔板 Kt' '按参数跳过'
} else {
    $ktDir = Join-Path $Root '算例\带孔板'
    $ktPy = Join-Path $ktDir 'run_kt.py'
    $r = Invoke-Tool $Py @($ktPy) $ktDir
    $kt = $null
    if ($r.Output -match 'Kt\s*\(相对净截面\)\s*=\s*([\d.]+)') { $kt = [double]$Matches[1] }
    $ok = ($null -ne $kt) -and ($kt -ge 2.38) -and ($kt -le 2.47)
    if ($null -ne $kt) {
        $detail = 'Kt=' + $kt + '（期望 2.38–2.47）'
    } else {
        $tail = $r.Output
        if ($tail.Length -gt 300) { $tail = $tail.Substring($tail.Length - 300) }
        $detail = '未解析到 Kt，输出尾部：' + $tail
    }
    Result '带孔板 Kt' $ok $detail
}

# ---------- 4. 疲劳脚本 ----------
if ($SkipFatigue) {
    SkipStep '疲劳脚本' '按参数跳过'
} else {
    $fatPy = Join-Path $Root 'tools\疲劳\fatigue.py'
    $csv = Join-Path $Root 'tools\测试\cube_tension_stress.csv'
    $outCsv = Join-Path $Work 'fatigue.csv'
    Remove-Item $outCsv -Force -ErrorAction SilentlyContinue
    $r = Invoke-Tool $Py @($fatPy, $csv, '--uts', '400', '--ratio', '0', '-o', $outCsv) $Work
    $ok = (Test-Path $outCsv) -and ($r.Output -match '\[OK\] 评定')
    $detail = 'exit=' + $r.Exit
    if (Test-Path $outCsv) {
        $line = Get-Content $outCsv | Select-Object -Skip 1 -First 1
        if ($line) { $detail = $line }
    }
    Result '疲劳脚本' $ok $detail
}

# ---------- 5. Gmsh ----------
if (Test-Path $Gmsh) {
    $r = Invoke-Tool $Gmsh @('--version') $Work
    $ver = $r.Output.Trim()
    Result 'Gmsh' ($ver -match '^\d+\.\d+') $ver
} else {
    Result 'Gmsh' $false ('找不到 ' + $Gmsh)
}

# ---------- 汇总 ----------
Write-Host ''
Write-Host ('===== 结果：' + $script:pass + ' 通过 / ' + $script:fail + ' 失败 / ' + $script:skip + ' 跳过 =====') -ForegroundColor Cyan
if ($script:fail -gt 0) {
    Write-Host '环境异常，先排查失败项再开始新任务。' -ForegroundColor Red
    exit 1
}
Write-Host '环境正常。' -ForegroundColor Green
exit 0
