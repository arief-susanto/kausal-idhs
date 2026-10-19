# terbitkan_repo.ps1 - menerbitkan folder proyek Kausal IDHS ke GitHub (lalu Zenodo)
#
# Jalankan dari terminal VS Code, di folder proyek (folder yang berisi config.py):
#   Tahap 1 (unggah ke GitHub):     powershell -ExecutionPolicy Bypass -File .\terbitkan_repo.ps1
#   Tahap 2 (setelah Zenodo aktif): powershell -ExecutionPolicy Bypass -File .\terbitkan_repo.ps1 -Rilis
#
# Skrip ini TIDAK mengunggah data IDHS. Ia berhenti bila menemukan file data DHS
# di dalam git, termasuk di riwayat commit lama.

param([switch]$Rilis, [string]$NamaRepo = "kausal-idhs", [string]$TagRilis = "v1.0-resti")
$ErrorActionPreference = "Continue"   # perintah git/gh diperiksa lewat $LASTEXITCODE
function Info($m) { Write-Host "==> $m" -ForegroundColor Cyan }
function Gagal($m) { Write-Host "BERHENTI: $m" -ForegroundColor Red; exit 1 }

# 0. Prasyarat
if (-not (Test-Path ".\config.py")) { Gagal "Jalankan skrip ini dari folder proyek yang berisi config.py." }
foreach ($alat in "git", "gh") {
  if (-not (Get-Command $alat -ErrorAction SilentlyContinue)) {
    Write-Host "Program '$alat' belum terpasang. Pasang dengan perintah berikut, tutup lalu buka ulang VS Code:" -ForegroundColor Yellow
    Write-Host "  winget install --id Git.Git -e"
    Write-Host "  winget install --id GitHub.cli -e"
    exit 1
  }
}

# 1. Login GitHub (sekali saja; browser akan terbuka)
gh auth status 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { Info "Login ke GitHub: pilih GitHub.com > HTTPS > Login with a web browser"; gh auth login }
$pengguna = (gh api user --jq .login).Trim()
Info "Akun GitHub: $pengguna"

if ($Rilis) {
  # ---------------- TAHAP 2: buat rilis -> Zenodo membuat DOI otomatis
  Info "Membuat rilis $TagRilis (Zenodo akan mengarsipkannya dan memberi DOI)"
  git push origin $TagRilis
  gh release create $TagRilis --title "Kausal IDHS $TagRilis (Jurnal RESTI submission)" `
    --notes "Code and locked analysis plan for the RESTI manuscript. All reported numbers come from tag v-paper1; this release adds metadata (README, LICENSE, CITATION.cff, .zenodo.json) and mcnemar_m2m3.py. IDHS microdata are not included."
  Info "Selesai. Tunggu 1-5 menit, lalu buka https://zenodo.org/account/settings/github/ untuk melihat DOI."
  exit 0
}

# ---------------- TAHAP 1: siapkan dan unggah
# 2. Isi nama pengguna di CITATION.cff
if (Test-Path ".\CITATION.cff") {
  (Get-Content .\CITATION.cff -Raw).Replace("GITHUB_USERNAME", $pengguna) | Set-Content .\CITATION.cff -Encoding UTF8 -NoNewline
}

# 3. Siapkan git
if (-not (Test-Path ".\.git")) {
  Info "Folder ini belum memakai git; membuat repositori baru"
  git init -b main | Out-Null
}
$pola = '\.(dta|sav|sas7bdat|dat|zip)$'

# 4. Periksa data DHS di riwayat git (commit lama ikut terunggah!)
$riwayat = git log --all --name-only --pretty=format: 2>$null | Where-Object { $_ -match $pola -or $_ -match '^data/' } | Sort-Object -Unique
if ($riwayat) {
  Write-Host "File berikut pernah di-commit dan akan ikut terunggah:" -ForegroundColor Red
  $riwayat | ForEach-Object { Write-Host "  $_" }
  Gagal "Riwayat git memuat data DHS. Jangan unggah; minta bantuan untuk membersihkan riwayat (git filter-repo) dulu."
}

# 5. Commit file metadata dan kode
git add -A
$siap = git diff --cached --name-only | Where-Object { $_ -match $pola -or $_ -match '^data/' }
if ($siap) { $siap | ForEach-Object { Write-Host "  $_" }; Gagal "File data DHS akan ikut ter-commit. Periksa .gitignore." }
Info "Daftar file yang akan diunggah:"
git ls-files
$jawab = Read-Host "Lanjutkan unggah? Pastikan tidak ada data IDHS dalam daftar di atas (y/n)"
if ($jawab -ne "y") { Gagal "Dibatalkan oleh pengguna." }
git diff --cached --quiet; if ($LASTEXITCODE -ne 0) { git commit -m "Add repository metadata for RESTI submission" | Out-Null }

# 6. Tag
if (-not (git tag --list "v-paper1")) {
  Write-Host "PERINGATAN: tag v-paper1 tidak ditemukan, padahal naskah merujuk ke tag itu (commit b077ace)." -ForegroundColor Yellow
}
if (-not (git tag --list $TagRilis)) { git tag $TagRilis }

# 7. Buat repo publik di GitHub dan unggah
gh repo view "$pengguna/$NamaRepo" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
  Info "Membuat repositori publik github.com/$pengguna/$NamaRepo"
  gh repo create $NamaRepo --public --source . --remote origin --description "Design-based causal graph discovery and confounder selection for complex survey data (IDHS 2017)"
}
$cabang = (git branch --show-current).Trim()
git push -u origin $cabang
git push origin --tags

Write-Host ""
Write-Host "TAHAP 1 SELESAI. URL GitHub untuk naskah: https://github.com/$pengguna/$NamaRepo" -ForegroundColor Green
Write-Host "Langkah berikut (di browser, sekali saja):"
Write-Host "  1. Buka https://zenodo.org lalu Log in > Log in with GitHub."
Write-Host "  2. Buka https://zenodo.org/account/settings/github/ lalu klik 'Sync now'."
Write-Host "  3. Geser tombol ON di samping $pengguna/$NamaRepo."
Write-Host "  4. Kembali ke VS Code dan jalankan: powershell -ExecutionPolicy Bypass -File .\terbitkan_repo.ps1 -Rilis"
