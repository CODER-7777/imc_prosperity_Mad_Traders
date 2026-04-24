# ============================================================
# Fix Script - Cherry-pick organized structure onto main
# ============================================================

$env:GIT_PAGER = "cat"

Set-Location "D:\PROSPERITY"

Write-Host "=== Step 1: Cherry-pick the reorganization commit onto main ===" -ForegroundColor Cyan
git checkout main

# The reorganization commit (de46c19) is on round_2 branch
# Cherry-pick it onto main
git cherry-pick de46c19 --no-commit

Write-Host ""
Write-Host "=== Step 2: Clean up leftover files ===" -ForegroundColor Cyan

# Remove old leftovers
if (Test-Path "Round_1_Sol_182426") { Remove-Item -Recurse -Force "Round_1_Sol_182426" }
if (Test-Path "reorganize.ps1") { Remove-Item -Force "reorganize.ps1" }

Write-Host ""
Write-Host "=== Step 3: Commit and push ===" -ForegroundColor Cyan

git add -A
git commit -m "chore: reorganize repo - round-based folder structure

- round1/strategy.py = v3_trend_max_long.py (R1 winner)
- round2/strategy.py = v4_round_2_strategy.py (R2 winner)
- round3-5/ = templates ready for future rounds
- tools/ = shared datamodel and utilities
- Comprehensive README with workflow
- .gitignore added"

git push origin main

Write-Host ""
Write-Host "=== Step 4: Verify ===" -ForegroundColor Cyan
Write-Host "Files on main:" -ForegroundColor Yellow
git ls-tree --name-only -r HEAD

Write-Host ""
Write-Host "Branches:" -ForegroundColor Yellow
git branch -a

Write-Host ""
Write-Host "DONE!" -ForegroundColor Green
