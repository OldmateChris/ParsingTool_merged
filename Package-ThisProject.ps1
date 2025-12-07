$ErrorActionPreference = 'Stop'

# Path to the shared generic packager
$packager = "C:\00.Developer\Scripts\Package-Project.ps1"

# This project’s root is the folder where this wrapper lives
$projectRoot = $PSScriptRoot

# Where to put the zip
$outputDir = "C:\00.Developer\Projects"

Write-Host "Using packager: $packager"
Write-Host "Project root : $projectRoot"
Write-Host "Output dir   : $outputDir"

& $packager -ProjectRoot $projectRoot -OutputDir $outputDir
