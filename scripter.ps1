
$ErrorActionPreference = "Stop"

# ============================================================
# WAKALA SMART - BACKEND FILE INVENTORY
# Ordered engineering review report
# ============================================================

$ProjectRoot = Get-Location
$BackendPath = Join-Path $ProjectRoot "backend"
$ReportPath = Join-Path $ProjectRoot "BACKEND_FILE_INVENTORY.txt"

if (-not (Test-Path $BackendPath -PathType Container)) {
    Write-Host "ERROR: backend directory not found." -ForegroundColor Red
    exit 1
}

# Engineering review order
$OrderedDirectories = @(
    "backend"
    "backend/app"
    "backend/app/core"
    "backend/app/db"
    "backend/app/models"
    "backend/app/repositories"
    "backend/app/schemas"
    "backend/app/services"
    "backend/app/workers"
    "backend/app/modules"
    "backend/app/modules/auth"
    "backend/app/modules/security_tokens"
    "backend/app/modules/platform_admin"
    "backend/app/modules/tenants"
    "backend/app/modules/members"
    "backend/app/modules/profiles"
    "backend/app/modules/accounts"
    "backend/app/modules/ledger"
    "backend/app/modules/transactions"
    "backend/app/modules/sms_ingestion"
    "backend/app/modules/grace_engine"
    "backend/app/modules/capital"
    "backend/app/modules/expenses"
    "backend/app/modules/floats"
    "backend/app/modules/debtors"
    "backend/app/modules/returns"
    "backend/app/modules/daily_registers"
    "backend/app/modules/archives"
    "backend/app/modules/analytics"
    "backend/app/modules/notifications"
    "backend/app/modules/subscriptions"
    "backend/app/modules/exports"
    "backend/app/modules/audit"
    "backend/app/api"
    "backend/app/api/v1"
    "backend/migrations"
    "backend/migrations/versions"
    "backend/scripts"
    "backend/tests"
    "backend/tests/unit"
    "backend/tests/integration"
    "backend/docs"
    "docs"
)

# Files included in inventory
$AllowedExtensions = @(
    ".py", ".toml", ".ini", ".md", ".mako",
    ".yaml", ".yml", ".txt", ".json", ".sql",
    ".ps1", ".sh", ".dockerfile"
)

$AllFiles = Get-ChildItem -LiteralPath $BackendPath -Recurse -File -Force |
    Where-Object {
        $_.Extension.ToLowerInvariant() -in $AllowedExtensions -or
        $_.Name -in @(
            "Dockerfile",
            "Makefile",
            ".env.example",
            ".gitignore"
        )
    }

$AllDirectories = Get-ChildItem -LiteralPath $BackendPath -Recurse -Directory -Force

$RelativeFiles = foreach ($File in $AllFiles) {
    $RelativePath = $File.FullName.Substring($ProjectRoot.Path.Length + 1)
    [PSCustomObject]@{
        Directory = (Split-Path $RelativePath -Parent).Replace("\", "/")
        FileName  = $File.Name
        FullPath  = $RelativePath.Replace("\", "/")
        Extension = $File.Extension
    }
}

$RelativeDirectories = foreach ($Directory in $AllDirectories) {
    $RelativePath = $Directory.FullName.Substring($ProjectRoot.Path.Length + 1)
    $RelativePath.Replace("\", "/")
}

# Directory order: known directories first, unknown directories afterwards
$DirectoryOrder = @{}
for ($i = 0; $i -lt $OrderedDirectories.Count; $i++) {
    $DirectoryOrder[$OrderedDirectories[$i]] = $i
}

$GroupedDirectories = @(
    $RelativeDirectories |
        Sort-Object {
            if ($DirectoryOrder.ContainsKey($_)) {
                $DirectoryOrder[$_]
            }
            else {
                9999
            }
        }, { $_ }
)

$Report = [System.Collections.Generic.List[string]]::new()

$Report.Add("============================================================")
$Report.Add("WAKALA SMART - BACKEND FILE INVENTORY")
$Report.Add("Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
$Report.Add("Project: $($ProjectRoot.Path)")
$Report.Add("Backend: $BackendPath")
$Report.Add("============================================================")
$Report.Add("")
$Report.Add("REVIEW ORDER:")
$Report.Add("01. Configuration and core")
$Report.Add("02. Database")
$Report.Add("03. Models and enums")
$Report.Add("04. Security and authentication")
$Report.Add("05. Tenant and membership")
$Report.Add("06. Financial modules and ledger")
$Report.Add("07. Business modules")
$Report.Add("08. API and routing")
$Report.Add("09. Workers and background jobs")
$Report.Add("10. Migrations")
$Report.Add("11. Scripts")
$Report.Add("12. Tests")
$Report.Add("13. Documentation")
$Report.Add("")
$Report.Add("============================================================")
$Report.Add("DIRECTORY-BY-DIRECTORY FILE LIST")
$Report.Add("============================================================")
$Report.Add("")

$Counter = 0

# Include backend root and all discovered directories
$DirectoriesToPrint = @("backend") + $GroupedDirectories

foreach ($Directory in $DirectoriesToPrint) {

    $Report.Add("")
    $Report.Add("------------------------------------------------------------")
    $Report.Add("DIRECTORY: $Directory")
    $Report.Add("------------------------------------------------------------")

    $DirectoryFiles = @(
        $RelativeFiles |
            Where-Object { $_.Directory -eq $Directory } |
            Sort-Object FileName
    )

    if ($DirectoryFiles.Count -eq 0) {
        $Report.Add("  [EMPTY DIRECTORY]")
        continue
    }

    foreach ($File in $DirectoryFiles) {
        $Counter++
        $Report.Add(("{0:D3}. {1}" -f $Counter, $File.FileName))
        $Report.Add("     PATH: $($File.FullPath)")
    }
}

$Report.Add("")
$Report.Add("============================================================")
$Report.Add("SUMMARY")
$Report.Add("============================================================")
$Report.Add("Total files: $($RelativeFiles.Count)")
$Report.Add("Total directories: $($RelativeDirectories.Count + 1)")
$Report.Add("Empty directories: $((@($DirectoriesToPrint | Where-Object {
    @($RelativeFiles | Where-Object { $_.Directory -eq $_ }).Count -eq 0
})).Count)")
$Report.Add("============================================================")

$Report | Set-Content -LiteralPath $ReportPath -Encoding UTF8

Write-Host ""
Write-Host "BACKEND INVENTORY COMPLETED" -ForegroundColor Green
Write-Host "Total files: $($RelativeFiles.Count)" -ForegroundColor Cyan
Write-Host "Report: $ReportPath" -ForegroundColor Yellow
Write-Host ""
Write-Host "Opening report..." -ForegroundColor Green

notepad $ReportPath
