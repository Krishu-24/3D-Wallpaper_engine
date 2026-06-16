$ErrorActionPreference = "Stop"

$MediaPipeRoot = "C:\dev\mediapipe"
$BazelCache = "C:\bazel_cache_mp1020"
$GitBash = "C:\Program Files\Git\bin\bash.exe"

function Prepend-ExistingPath {
    param([string]$Path)

    if (Test-Path $Path) {
        $env:PATH = "$Path;$env:PATH"
        Write-Host "Added to PATH: $Path"
    }
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$SourceAppDir = Join-Path $RepoRoot "cpp\mediapipe_bazel\wallpaper_mediapipe_runner"
$ModelPath = Join-Path $RepoRoot "models\face_landmarker.task"

if (-not (Test-Path $MediaPipeRoot)) {
    throw "MediaPipe checkout not found at $MediaPipeRoot."
}
if (-not (Test-Path $GitBash)) {
    throw "Git Bash not found at $GitBash."
}
if (-not (Test-Path $ModelPath)) {
    throw "Model file not found at $ModelPath."
}
if (-not (Test-Path (Join-Path $SourceAppDir "BUILD.bazel"))) {
    throw "Canonical MediaPipe Bazel app is missing BUILD.bazel at $SourceAppDir."
}
if (-not (Test-Path (Join-Path $SourceAppDir "main.cpp"))) {
    throw "Canonical MediaPipe Bazel app is missing main.cpp at $SourceAppDir."
}

$env:BAZEL_SH = $GitBash

$Py = (& py -3.12 -c "import sys; print(sys.executable)").Trim()
if (-not $Py) {
    throw "Could not resolve Python 3.12 executable with py -3.12."
}
Write-Host "Using Python: $Py"

$OpenCvPaths = @(
    "C:\opencv\build\x64\vc16\bin",
    "C:\opencv\build\x64\vc15\bin",
    "C:\opencv\build\x64\vc16\lib",
    "$env:USERPROFILE\Downloads\opencv\build\x64\vc16\bin",
    "$env:USERPROFILE\Downloads\opencv\build\x64\vc16\lib"
)

foreach ($path in $OpenCvPaths) {
    Prepend-ExistingPath $path
}

$DestinationAppDir = Join-Path $MediaPipeRoot "mediapipe\experiments\wallpaper_mediapipe_runner"
$DestinationParent = Split-Path $DestinationAppDir -Parent
New-Item -ItemType Directory -Force -Path $DestinationParent | Out-Null

if (Test-Path $DestinationAppDir) {
    Remove-Item -LiteralPath $DestinationAppDir -Recurse -Force
}
Copy-Item -LiteralPath $SourceAppDir -Destination $DestinationAppDir -Recurse -Force
Write-Host "Copied app to $DestinationAppDir"

$Label = "//mediapipe/experiments/wallpaper_mediapipe_runner:wallpaper_mediapipe_runner"

Set-Location $MediaPipeRoot

$BazelArgs = @(
    "--output_user_root=$BazelCache",
    "build",
    "-c",
    "opt",
    "--conlyopt=/std:c11",
    "--conlyopt=/experimental:c11atomics",
    "--cxxopt=/Zc:preprocessor",
    "--host_cxxopt=/Zc:preprocessor",
    "--define=protobuf_allow_msvc=true",
    "--repo_env=PYTHON_BIN_PATH=$Py",
    "--action_env=PYTHON_BIN_PATH=$Py",
    "--repo_env=HERMETIC_PYTHON_VERSION=3.12",
    "--define=MEDIAPIPE_DISABLE_GPU=1",
    $Label
)

Write-Host "Building $Label"
& bazelisk @BazelArgs

$ExePath = Join-Path $MediaPipeRoot "bazel-bin\mediapipe\experiments\wallpaper_mediapipe_runner\wallpaper_mediapipe_runner.exe"
if (-not (Test-Path $ExePath)) {
    throw "Built executable not found at $ExePath."
}

$ExeDir = Split-Path $ExePath -Parent
foreach ($path in $OpenCvPaths) {
    if (Test-Path $path) {
        Get-ChildItem -LiteralPath $path -Filter "opencv*.dll" -File -ErrorAction SilentlyContinue |
            ForEach-Object {
                Copy-Item -LiteralPath $_.FullName -Destination $ExeDir -Force
                Write-Host "Copied DLL: $($_.Name)"
            }
    }
}

Write-Host "Running $ExePath"
& $ExePath $ModelPath
