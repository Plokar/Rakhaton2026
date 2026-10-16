<#
.SYNOPSIS
  Hackathon OS - Vyvojarsky skript pro Windows PowerShell
.DESCRIPTION
  Umoznuje snadno spustit, zastavit, seedovat a resetovat lokalni Docker prostredi.
.EXAMPLE
  .\dev.ps1 up
  .\dev.ps1 seed
  .\dev.ps1 reset
  .\dev.ps1 down
#>

param (
    [Parameter(Position = 0)]
    [ValidateSet("up", "down", "seed", "reset", "build", "logs", "status", "test")]
    [string]$Command = "up"
)

$ComposeFile = "docker-compose.dev.yml"

switch ($Command) {
    "up" {
        Write-Host ">> Spoustim Hackathon OS v dev modu (hot-reload)..." -ForegroundColor Cyan
        if (-not (Test-Path ".env")) {
            Write-Host "[!] .env nenalezen, kopiruji z .env.dev.example..." -ForegroundColor Yellow
            Copy-Item ".env.dev.example" ".env"
        }
        docker compose -f $ComposeFile up --build -d
        Write-Host ""
        Write-Host "[OK] Vsechny sluzby bezi!" -ForegroundColor Green
        Write-Host "   Frontend:          http://localhost:3000" -ForegroundColor White
        Write-Host "   Swagger UI:        http://localhost:8000/api/docs/" -ForegroundColor White
        Write-Host "   Backend API:       http://localhost:8000/api/" -ForegroundColor White
        Write-Host "   Django Admin:      http://localhost:8000/admin/ (admin / admin123456)" -ForegroundColor White
        Write-Host "   Mailhog E-maily:   http://localhost:8025" -ForegroundColor White
        Write-Host "   Traefik Dashboard: http://localhost:8080" -ForegroundColor White
    }

    "down" {
        Write-Host "[*] Zastavuji kontejnery..." -ForegroundColor Yellow
        docker compose -f $ComposeFile down
        Write-Host "[OK] Vse zastaveno." -ForegroundColor Green
    }

    "seed" {
        Write-Host "[*] Spoustim seedovani demo dat v backendu..." -ForegroundColor Cyan
        docker compose -f $ComposeFile exec backend python manage.py seed_demo_data
    }

    "reset" {
        Write-Host "[!] Resetuji databazi a provadim nove migrace..." -ForegroundColor Red
        docker compose -f $ComposeFile down -v
        docker compose -f $ComposeFile up --build -d
        Start-Sleep -Seconds 5
        docker compose -f $ComposeFile exec backend python manage.py migrate
        docker compose -f $ComposeFile exec backend python manage.py seed_demo_data
        Write-Host "[OK] Databaze byla resetovana a naplnena demo daty!" -ForegroundColor Green
    }

    "build" {
        Write-Host "[*] Prestavuji kontejnery..." -ForegroundColor Cyan
        docker compose -f $ComposeFile build --no-cache
    }

    "logs" {
        docker compose -f $ComposeFile logs -f
    }

    "status" {
        docker compose -f $ComposeFile ps
    }

    "test" {
        Write-Host "[*] Spoustim testy..." -ForegroundColor Cyan
        docker compose -f $ComposeFile exec backend pytest
    }
}
