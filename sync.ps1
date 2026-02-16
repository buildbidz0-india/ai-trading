param (
    [string]$Message = "Update from automation script"
)

Write-Host "--- Starting Git sync ---" -ForegroundColor Cyan

# Add and Commit
Write-Host "Adding changes..."
git add -A
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to add changes." -ForegroundColor Red
    exit 1
}

$status = git status --porcelain
if ($status) {
    Write-Host "Committing changes..."
    git commit -m "$Message"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Failed to commit changes." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "No changes to commit." -ForegroundColor Green
}

# Sync with remote
Write-Host "Syncing with remote..."
git pull --rebase origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to pull changes." -ForegroundColor Red
    exit 1
}

git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to push changes." -ForegroundColor Red
    exit 1
}

Write-Host "Sync complete!" -ForegroundColor Green
