# ============================================================
# IMC Prosperity Repo Reorganization Script
# Run this from PowerShell in D:\PROSPERITY
# ============================================================
# This script:
#   1. Moves data/docs into the new round folders
#   2. Creates trial branches with experimental scripts
#   3. Cleans up old directories from main
#   4. Commits everything
# ============================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  IMC Prosperity Repo Reorganization" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location "D:\PROSPERITY"

# ------ STEP 1: Move data files into new structure ------
Write-Host "[1/6] Moving data files..." -ForegroundColor Yellow

# Round 1 data
Copy-Item "ROUND1\*.csv" "round1\data\" -Force
Write-Host "  -> Copied R1 CSVs to round1/data/"

# Round 1 docs (from Round_1_tries)
Copy-Item "Round_1_tries\Game_Mechanics_Overview_.pdf" "round1\docs\" -Force -ErrorAction SilentlyContinue
Copy-Item "Round_1_tries\Prosperity_4_Wiki.pdf" "round1\docs\" -Force -ErrorAction SilentlyContinue
Write-Host "  -> Copied R1 docs to round1/docs/"

# Round 2 data
Copy-Item "ROUND_2\*.csv" "round2\data\" -Force
Write-Host "  -> Copied R2 CSVs to round2/data/"

# Round 2 docs
Copy-Item "ROUND_2\Round_2.pdf" "round2\docs\" -Force -ErrorAction SilentlyContinue
Copy-Item "ROUND_2\Writing_an_Algorithm_in_Python.pdf" "round2\docs\" -Force -ErrorAction SilentlyContinue
Write-Host "  -> Copied R2 docs to round2/docs/"

# ------ STEP 2: Stage everything new on main first ------
Write-Host ""
Write-Host "[2/6] Staging new structure on main..." -ForegroundColor Yellow

git add round1/ round2/ round3/ round4/ round5/ tools/ .gitignore README.md
git commit -m "chore: reorganize repo - new round-based folder structure

- round1/strategy.py = v3_trend_max_long.py (R1 winner)
- round2/strategy.py = v4_round_2_strategy.py (R2 winner)
- round3-5/ = templates ready for future rounds
- tools/ = shared datamodel and utilities
- Added comprehensive README with workflow
- Added .gitignore"

Write-Host "  -> Committed new structure on main" -ForegroundColor Green

# ------ STEP 3: Create round1/trials branch ------
Write-Host ""
Write-Host "[3/6] Creating round1/trials branch..." -ForegroundColor Yellow

git checkout -b round1/trials
# Copy all trial scripts to a trials/ folder on this branch
New-Item -ItemType Directory -Path "trials" -Force | Out-Null
Copy-Item "Round_1_tries\algo.py" "trials\" -Force -ErrorAction SilentlyContinue
Copy-Item "Round_1_tries\v2_optimized_ema_limit20.py" "trials\" -Force -ErrorAction SilentlyContinue
Copy-Item "Round_1_tries\v4_perfect_sniper.py" "trials\" -Force -ErrorAction SilentlyContinue
Copy-Item "Round_1_tries\v5_mode.py" "trials\" -Force -ErrorAction SilentlyContinue
Copy-Item "Round_1_tries\v6_general_approach.py" "trials\" -Force -ErrorAction SilentlyContinue
Copy-Item "Round_1_tries\v7_trader.py" "trials\" -Force -ErrorAction SilentlyContinue
Copy-Item "Round_1_tries\v8_trader.py" "trials\" -Force -ErrorAction SilentlyContinue
Copy-Item "Round_1_tries\v9_trader.py" "trials\" -Force -ErrorAction SilentlyContinue
Copy-Item "Round_1_tries\datamodel.py" "trials\" -Force -ErrorAction SilentlyContinue
Copy-Item "Round_1_tries\extract_pdf.py" "trials\" -Force -ErrorAction SilentlyContinue

git add trials/
git commit -m "archive: Round 1 trial strategies (v2-v9, algo)

All experimental strategies from Round 1 development.
Winner was v3_trend_max_long.py (on main branch)."

Write-Host "  -> Created round1/trials with all experiments" -ForegroundColor Green

# ------ STEP 4: Create round2/trials branch ------
Write-Host ""
Write-Host "[4/6] Creating round2/trials branch..." -ForegroundColor Yellow

git checkout main
git checkout -b round2/trials
New-Item -ItemType Directory -Path "trials" -Force | Out-Null

# Add any R2 experimental scripts here
# (v4_round_2_strategy.py is the winner, already on main)
Copy-Item "ROUND_2\read_pdf.py" "trials\" -Force -ErrorAction SilentlyContinue

git add trials/
git commit -m "archive: Round 2 trial strategies

Experimental files from Round 2 development.
Winner was v4_round_2_strategy.py (on main branch)." --allow-empty

Write-Host "  -> Created round2/trials" -ForegroundColor Green

# ------ STEP 5: Clean up old directories on main ------
Write-Host ""
Write-Host "[5/6] Cleaning up old directories on main..." -ForegroundColor Yellow

git checkout main

# Remove old messy directories
Remove-Item -Recurse -Force "ROUND1" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "ROUND_2" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "Round_1_tries" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "Logs" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "imc_prosperity2" -ErrorAction SilentlyContinue
Remove-Item -Force "imc_prosperity2.zip" -ErrorAction SilentlyContinue
Remove-Item -Force "v3_trend_max_long.py" -ErrorAction SilentlyContinue

git add -A
git commit -m "chore: clean up old directory structure

Removed: ROUND1/, ROUND_2/, Round_1_tries/, Logs/,
         imc_prosperity2/, imc_prosperity2.zip, v3_trend_max_long.py

All winning strategies are now in roundN/strategy.py
All trial strategies are on roundN/trials branches"

Write-Host "  -> Cleaned up old directories" -ForegroundColor Green

# ------ STEP 6: Push everything ------
Write-Host ""
Write-Host "[6/6] Pushing to remote..." -ForegroundColor Yellow

git push origin main
git push origin round1/trials
git push origin round2/trials

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  DONE! Repository is reorganized." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Structure on main:" -ForegroundColor Cyan
Write-Host "  round1/strategy.py  <- R1 winner (v3_trend_max_long)"
Write-Host "  round2/strategy.py  <- R2 winner (v4_round_2_strategy)"
Write-Host "  round3/strategy.py  <- Template (ready for R3)"
Write-Host "  round4/strategy.py  <- Template (ready for R4)"
Write-Host "  round5/strategy.py  <- Template (ready for R5)"
Write-Host ""
Write-Host "Branches:" -ForegroundColor Cyan
Write-Host "  main             <- Winners only"
Write-Host "  round1/trials    <- R1 experiments"
Write-Host "  round2/trials    <- R2 experiments"
Write-Host ""
Write-Host "When Round 3 starts, run:" -ForegroundColor Magenta
Write-Host "  git checkout -b round3/trials" -ForegroundColor White
