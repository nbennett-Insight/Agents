############################################################
# CONFIG
############################################################
$exportRoot          = "E:\VSCode-Root\onenote"
$targetNotebookName  = "Bennett-Notes"   # from Graph displayName

############################################################
# Helper: Clean names for Windows paths
############################################################
function Clean-NameForPath {
    param(
        [Parameter(Mandatory = $true)][string]$Name
    )

    # Remove invalid filename chars: \ / : * ? " < > |
    $clean = $Name -replace '[\\/:*?"<>|]', '_'
    # Trim spaces and dots from ends
    $clean = $clean.Trim().TrimEnd('.')
    if ([string]::IsNullOrWhiteSpace($clean)) {
        $clean = "Untitled"
    }
    return $clean
}

############################################################
# Step 1: Device-code auth to Microsoft Graph
############################################################
function Get-GraphAccessToken {
    param(
        [Parameter(Mandatory = $true)][string]$ClientId,
        [Parameter(Mandatory = $true)][string]$TenantId,
        [string]$Scope = "https://graph.microsoft.com/.default"
    )

    # Device code flow
    $deviceCodeParams = @{
        client_id = $ClientId
        scope     = "https://graph.microsoft.com/.default offline_access"
    }

    $deviceCodeResponse = Invoke-RestMethod `
        -Uri "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/devicecode" `
        -Method POST `
        -Body $deviceCodeParams

    Write-Host ""
    Write-Host "== Device login =="
    Write-Host "Go to: $($deviceCodeResponse.verification_uri)"
    Write-Host "Enter code: $($deviceCodeResponse.user_code)"
    Write-Host ""

    $tokenParams = @{
        grant_type  = "urn:ietf:params:oauth:grant-type:device_code"
        client_id   = $ClientId
        device_code = $deviceCodeResponse.device_code
    }

    while ($true) {
        Start-Sleep -Seconds $deviceCodeResponse.interval

        try {
            $tokenResponse = Invoke-RestMethod `
                -Uri "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token" `
                -Method POST `
                -Body $tokenParams

            if ($tokenResponse.access_token) {
                return $tokenResponse.access_token
            }
        }
        catch {
            $errorText = $_.ErrorDetails.Message
            if ($errorText -notmatch "authorization_pending") {
                Write-Host "Error during token acquisition: $errorText"
                throw
            }
        }
    }
}

############################################################
# MAIN
############################################################

# 1. Prepare export root
if (-not (Test-Path $exportRoot)) {
    New-Item -ItemType Directory -Path $exportRoot | Out-Null
}

# 2. Tenant + Client ID
$tenantId = "organizations"  # or your tenant GUID if needed
$clientId = "04f0c124-f2bc-4f59-9e9b-3d0a3f9c17e3"  # public MS Graph client ID

Write-Host "Signing in to Microsoft Graph..."
$accessToken = Get-GraphAccessToken -ClientId $clientId -TenantId $tenantId

$headers = @{
    "Authorization" = "Bearer $accessToken"
    "Accept"        = "application/json"
}

############################################################
# Step 2: Find the target notebook
############################################################
Write-Host "Retrieving notebooks..."
$notebooksUrl = "https://graph.microsoft.com/v1.0/me/onenote/notebooks?`$top=200"

$notebooks = @()
do {
    $response = Invoke-RestMethod -Uri $notebooksUrl -Headers $headers -Method GET
    $notebooks += $response.value
    $notebooksUrl = $response.'@odata.nextLink'
} while ($notebooksUrl)

$targetNotebook = $notebooks | Where-Object { $_.displayName -eq $targetNotebookName }

if (-not $targetNotebook) {
    Write-Host "Notebook '$targetNotebookName' not found."
    exit 1
}

$notebookId       = $targetNotebook.id
$cleanNotebook    = Clean-NameForPath -Name $targetNotebook.displayName
$notebookRootPath = Join-Path $exportRoot $cleanNotebook

Write-Host "Target notebook ID: $notebookId"
Write-Host "Creating notebook root folder: $notebookRootPath"

New-Item -ItemType Directory -Path $notebookRootPath -Force | Out-Null

############################################################
# Step 3: Enumerate sections
############################################################
Write-Host "Retrieving sections for notebook '$($targetNotebook.displayName)'..."

$sectionsUrl = "https://graph.microsoft.com/v1.0/me/onenote/notebooks/$notebookId/sections?`$top=200"
$sections = @()

do {
    $response = Invoke-RestMethod -Uri $sectionsUrl -Headers $headers -Method GET
    $sections += $response.value
    $sectionsUrl = $response.'@odata.nextLink'
} while ($sectionsUrl)

if (-not $sections) {
    Write-Host "No sections found in notebook '$($targetNotebook.displayName)'."
    exit 0
}

foreach ($section in $sections) {
    $sectionName      = $section.displayName
    $cleanSectionName = Clean-NameForPath -Name $sectionName
    $sectionFolder    = Join-Path $notebookRootPath $cleanSectionName

    Write-Host "`nSection: $sectionName"
    Write-Host "Creating folder: $sectionFolder"
    New-Item -ItemType Directory -Path $sectionFolder -Force | Out-Null

    # Step 4: Enumerate pages in this section
    $sectionId  = $section.id
    $pagesUrl   = "https://graph.microsoft.com/v1.0/me/onenote/sections/$sectionId/pages?`$top=200"
    $allPages   = @()

    do {
        $pageResponse = Invoke-RestMethod -Uri $pagesUrl -Headers $headers -Method GET
        $allPages += $pageResponse.value
        $pagesUrl = $pageResponse.'@odata.nextLink'
    } while ($pagesUrl)

    if (-not $allPages) {
        Write-Host "  No pages in this section."
        continue
    }

    foreach ($page in $allPages) {
        $pageTitle      = $page.title
        $cleanPageTitle = Clean-NameForPath -Name $pageTitle

        # Optional: prefix with part of page ID to avoid duplicates
        $pageIdShort     = $page.id.Substring(0,8)
        $pageFolderName  = "$cleanPageTitle`__$pageIdShort"
        $pageFolderPath  = Join-Path $sectionFolder $pageFolderName

        Write-Host "  Page: $pageTitle"
        Write-Host "    Creating page folder: $pageFolderPath"

        New-Item -ItemType Directory -Path $pageFolderPath -Force | Out-Null

        # Later:
        #   HTML:   Join-Path $pageFolderPath "page.html"
        #   Images: Join-Path $pageFolderPath "images"
    }
}

Write-Host "`nDone building folder structure at: $exportRoot"
