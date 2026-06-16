$ErrorActionPreference = "Stop"

# Repo root = two folders above this script: cpp/scripts -> repo root
$RepoRoot = Resolve-Path "$PSScriptRoot\..\.."
$CppDir = Join-Path $RepoRoot "cpp"
$BuildDir = Join-Path $CppDir "build"

# OpenCV paths. Keep both because your system has used both during setup.
$OpenCvConfigCandidates = @(
    "C:\opencv\build\x64\vc16\lib",
    "$env:USERPROFILE\Downloads\opencv\build\x64\vc16\lib"
)

$OpenCvBinCandidates = @(
    "C:\opencv\build\x64\vc16\bin",
    "$env:USERPROFILE\Downloads\opencv\build\x64\vc16\bin"
)

$OpenCvDir = $OpenCvConfigCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $OpenCvDir) {
    throw "OpenCV config path not found. Checked: $($OpenCvConfigCandidates -join ', ')"
}

foreach ($binPath in $OpenCvBinCandidates) {
    if (Test-Path $binPath) {
        $env:PATH = "$binPath;$env:PATH"
    }
}

# Force this runner to use debug mouse mode.
$env:TRACKING_BACKEND = "debug_mouse"
$env:DEBUG_TRACKING = "true"

Set-Location $RepoRoot

Write-Host "Configuring CMake with OpenCV_DIR=$OpenCvDir"
cmake -S $CppDir -B $BuildDir -DOpenCV_DIR="$OpenCvDir"

Write-Host "Building debug_mouse_runner in Release mode..."
cmake --build $BuildDir --target debug_mouse_runner --config Release

$ExePath = Join-Path $BuildDir "Release\debug_mouse_runner.exe"

if (-not (Test-Path $ExePath)) {
    throw "debug_mouse_runner.exe not found at $ExePath"
}

Write-Host "Running debug_mouse_runner..."
& $ExePath