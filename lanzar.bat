@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM =====================================
REM Config hardcodeada (Gestor-De-Enlaces-para-NVDA)
REM =====================================
set "REPO_OWNER=AAyoubelbakhti"
set "REPO_NAME=Gestor-De-Enlaces-para-NVDA"
set "REPO=%REPO_OWNER%/%REPO_NAME%"


set "BUILD_CMD=scons"

REM =====================================
REM Verificaciones
REM =====================================
where git >nul 2>&1 || (echo ERROR: git no esta en PATH.& exit /b 1)
where gh  >nul 2>&1 || (echo ERROR: gh no esta en PATH.& exit /b 1)

if not "%BUILD_CMD%"=="" (
  for %%A in (%BUILD_CMD%) do set "BUILD_EXE=%%~A"
  where !BUILD_EXE! >nul 2>&1 || (echo ERROR: !BUILD_EXE! no esta en PATH.& exit /b 1)
)

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo ERROR: Ejecuta este .bat dentro del repo del addon.
  exit /b 1
)

REM =====================================
REM Pedir version/tag
REM =====================================
set "VERSION="
set /p VERSION=Introduce la version/tag (ej: v1.8): 
if "%VERSION%"=="" (
  echo ERROR: version vacia.
  exit /b 1
)

REM =====================================
REM Build (opcional)
REM =====================================
if not "%BUILD_CMD%"=="" (
  echo.
  echo ==== Ejecutando build: %BUILD_CMD% ====
  %BUILD_CMD%
  if errorlevel 1 (
    echo ERROR: fallo el build.
    exit /b 1
  )
)

REM =====================================
REM Detectar unico .nvda-addon
REM =====================================
set "ADDON_FILE="
for %%F in (*.nvda-addon) do (
  if defined ADDON_FILE (
    echo ERROR: hay mas de un .nvda-addon en la carpeta.
    exit /b 1
  )
  set "ADDON_FILE=%%F"
)

if not defined ADDON_FILE (
  echo ERROR: no se encontro ningun .nvda-addon en esta carpeta:
  echo %CD%
  exit /b 1
)

echo.
echo Addon encontrado: "%ADDON_FILE%"

REM =====================================
REM Git: add/commit/tag/push
REM =====================================
echo.
echo ==== Git add/commit/tag/push ====
git add -A
if errorlevel 1 (
  echo ERROR: git add fallo.
  exit /b 1
)

REM Commit solo si hay cambios staged
git diff --cached --quiet
if errorlevel 1 (
  git commit -m "Release %VERSION%"
  if errorlevel 1 (
    echo ERROR: commit fallo.
    exit /b 1
  )
) else (
  echo No hay cambios para commit. Continuo...
)

REM Crear tag (si ya existe, aborta)
git tag "%VERSION%" >nul 2>&1
if not errorlevel 1 (
  echo ERROR: El tag "%VERSION%" ya existe localmente.
  exit /b 1
)

git tag "%VERSION%"
if errorlevel 1 (
  echo ERROR: no se pudo crear el tag.
  exit /b 1
)

git push
if errorlevel 1 (
  echo ERROR: git push fallo.
  exit /b 1
)

git push origin "%VERSION%"
if errorlevel 1 (
  echo ERROR: git push del tag fallo.
  exit /b 1
)

REM =====================================
REM GitHub Release: crear + subir asset
REM =====================================
echo.
echo ==== GitHub release + upload ====
gh release view "%VERSION%" --repo "%REPO%" >nul 2>&1
if errorlevel 1 (
  gh release create "%VERSION%" "%ADDON_FILE%" --repo "%REPO%" --title "%VERSION%" --notes "Release %VERSION%"
  if errorlevel 1 (
    echo ERROR: no se pudo crear la release/subir el asset.
    exit /b 1
  )
) else (
  gh release upload "%VERSION%" "%ADDON_FILE%" --repo "%REPO%" --clobber
  if errorlevel 1 (
    echo ERROR: no se pudo subir/reemplazar el asset.
    exit /b 1
  )
)

echo.
echo ==========================
echo OK: Publicado %VERSION%
echo Repo: %REPO%
echo Asset: %ADDON_FILE%
echo ==========================
pause
endlocal
