#!/bin/bash
# Genera el instalador .msi de Market Ticker para Windows usando wixl
# (msitools), desde Linux. La app se instala por-usuario (sin UAC) en
# %LocalAppData%\Programs\Market Ticker con acceso directo en el menú
# inicio; el venv con las dependencias pip se crea en el primer arranque
# (setup.bat vía launcher.vbs), porque PyInstaller no cross-compila y un
# MSI no puede ejecutar pip de forma fiable durante la instalación.
#
# Requiere: wixl y uuidgen. En Ubuntu: sudo apt install wixl msitools
# (o exportar WIXL apuntando al binario).
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# La versión vive en frontend/main.py (APP_VERSION): única fuente de verdad
VERSION="$(sed -n 's/^APP_VERSION = "\([^"]*\)".*/\1/p' "$PROJECT_DIR/frontend/main.py")"
STAGE="$PROJECT_DIR/release/msi-build"
OUT="$PROJECT_DIR/release/market-ticker-${VERSION}.msi"
WIXL="${WIXL:-wixl}"
MSIBUILD="${MSIBUILD:-msibuild}"
UPGRADE_CODE="CF140DF6-3E87-4A6D-B16B-2B1EF41F600E"   # fijo: identifica el producto entre versiones

# GUID de componente estable, derivado del path (uuid v5 sobre namespace URL)
cguid() { uuidgen --sha1 --namespace @url --name "market-ticker/msi/$1" | tr a-z A-Z; }

rm -rf "$STAGE"
mkdir -p "$STAGE/backend" "$STAGE/assets" "$STAGE/config"

# ---- archivos de la app ----
cp "$PROJECT_DIR"/backend/{app.py,db.py,scraper.py,requirements.txt} "$STAGE/backend/"
cp "$PROJECT_DIR/frontend/main.py" "$STAGE/main.py"
cp "$PROJECT_DIR"/assets/{ticker.ico,ticker.png} "$STAGE/assets/"
cp "$PROJECT_DIR/config/config.json" "$STAGE/config/"
cp "$PROJECT_DIR/release/requirements.txt" "$STAGE/requirements.txt"
cp "$PROJECT_DIR"/installers/windows/{launcher.pyw,launcher.vbs,setup.bat,run.bat,INSTRUCCIONES.txt} "$STAGE/"

# ---- definición WiX ----
cat > "$STAGE/market-ticker.wxs" << EOF
<?xml version="1.0" encoding="utf-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="*" Name="Market Ticker" Manufacturer="Leandro R. Bergero"
           Version="$VERSION" Language="3082" UpgradeCode="$UPGRADE_CODE">
    <Package Description="Banner de cotizaciones en tiempo real"
             Comments="github.com/leabergero" InstallerVersion="200"
             Compressed="yes" InstallScope="perUser"/>
    <MajorUpgrade DowngradeErrorMessage="Ya hay una versión más nueva instalada."/>
    <Media Id="1" Cabinet="app.cab" EmbedCab="yes"/>

    <Icon Id="ticker.ico" SourceFile="assets/ticker.ico"/>
    <Property Id="ARPPRODUCTICON" Value="ticker.ico"/>
    <Property Id="ARPURLINFOABOUT" Value="https://github.com/leabergero"/>
    <Property Id="ARPNOMODIFY" Value="1"/>

    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="ProgramMenuFolder"/>
      <Directory Id="LocalAppDataFolder">
        <Directory Id="LADPrograms" Name="Programs">
          <Directory Id="INSTALLDIR" Name="Market Ticker">

            <Component Id="MainPy" Guid="$(cguid main.py)">
              <File Id="main.py" Name="main.py" Source="main.py"/>
            </Component>
            <Component Id="LauncherPyw" Guid="$(cguid launcher.pyw)">
              <File Id="launcher.pyw" Name="launcher.pyw" Source="launcher.pyw"/>
            </Component>
            <Component Id="LauncherVbs" Guid="$(cguid launcher.vbs)">
              <File Id="launcher.vbs" Name="launcher.vbs" Source="launcher.vbs"/>
              <Shortcut Id="StartMenuShortcut" Directory="ProgramMenuFolder"
                        Name="Market Ticker" WorkingDirectory="INSTALLDIR"
                        Target="[INSTALLDIR]launcher.vbs" Icon="ticker.ico"
                        Description="Banner de cotizaciones en tiempo real"/>
            </Component>
            <Component Id="SetupBat" Guid="$(cguid setup.bat)">
              <File Id="setup.bat" Name="setup.bat" Source="setup.bat"/>
            </Component>
            <Component Id="RunBat" Guid="$(cguid run.bat)">
              <File Id="run.bat" Name="run.bat" Source="run.bat"/>
            </Component>
            <Component Id="Reqs" Guid="$(cguid requirements.txt)">
              <File Id="requirements.txt" Name="requirements.txt" Source="requirements.txt"/>
            </Component>
            <Component Id="Instrucciones" Guid="$(cguid INSTRUCCIONES.txt)">
              <File Id="INSTRUCCIONES.txt" Name="INSTRUCCIONES.txt" Source="INSTRUCCIONES.txt"/>
            </Component>

            <Directory Id="BackendDir" Name="backend">
              <Component Id="BackendApp" Guid="$(cguid backend/app.py)">
                <File Id="backend_app.py" Name="app.py" Source="backend/app.py"/>
              </Component>
              <Component Id="BackendDb" Guid="$(cguid backend/db.py)">
                <File Id="backend_db.py" Name="db.py" Source="backend/db.py"/>
              </Component>
              <Component Id="BackendScraper" Guid="$(cguid backend/scraper.py)">
                <File Id="backend_scraper.py" Name="scraper.py" Source="backend/scraper.py"/>
              </Component>
              <Component Id="BackendReqs" Guid="$(cguid backend/requirements.txt)">
                <File Id="backend_requirements.txt" Name="requirements.txt" Source="backend/requirements.txt"/>
              </Component>
            </Directory>

            <Directory Id="AssetsDir" Name="assets">
              <Component Id="AssetIco" Guid="$(cguid assets/ticker.ico)">
                <File Id="ticker.ico" Name="ticker.ico" Source="assets/ticker.ico"/>
              </Component>
              <Component Id="AssetPng" Guid="$(cguid assets/ticker.png)">
                <File Id="ticker.png" Name="ticker.png" Source="assets/ticker.png"/>
              </Component>
            </Directory>

            <Directory Id="ConfigDir" Name="config">
              <Component Id="ConfigJson" Guid="$(cguid config/config.json)">
                <File Id="config.json" Name="config.json" Source="config/config.json"/>
              </Component>
            </Directory>

          </Directory>
        </Directory>
      </Directory>
    </Directory>

    <!-- Primer arranque automático al terminar la instalación: lanza
         launcher.vbs (sin venv todavía → setup.bat en consola visible;
         con venv → la app directa). launcher.pyw tiene un mutex que evita
         una segunda instancia si además lo relanza el updater.
         OJO: wixl no sabe generar custom actions tipo 34 (Directory +
         ExeCommand), así que acá solo va la secuencia; la fila de
         CustomAction se importa después con msibuild (ver el final). -->
    <InstallExecuteSequence>
      <Custom Action="LaunchApp" After="InstallFinalize">NOT Installed AND NOT REMOVE</Custom>
    </InstallExecuteSequence>

    <Feature Id="Complete" Level="1">
      <ComponentRef Id="MainPy"/>
      <ComponentRef Id="LauncherPyw"/>
      <ComponentRef Id="LauncherVbs"/>
      <ComponentRef Id="SetupBat"/>
      <ComponentRef Id="RunBat"/>
      <ComponentRef Id="Reqs"/>
      <ComponentRef Id="Instrucciones"/>
      <ComponentRef Id="BackendApp"/>
      <ComponentRef Id="BackendDb"/>
      <ComponentRef Id="BackendScraper"/>
      <ComponentRef Id="BackendReqs"/>
      <ComponentRef Id="AssetIco"/>
      <ComponentRef Id="AssetPng"/>
      <ComponentRef Id="ConfigJson"/>
    </Feature>
  </Product>
</Wix>
EOF

# ---- construir ----
(cd "$STAGE" && "$WIXL" -v -o "$OUT" market-ticker.wxs)

# ---- custom action LaunchApp (tipo 34+192 = exe en INSTALLDIR, asyncNoWait):
# wixl no la puede generar, se importa la tabla con msibuild (msitools).
# Los campos del .idt van separados por TAB.
printf 'Action\tType\tSource\tTarget\tExtendedType\ns72\ti2\tS72\tS255\tI4\nCustomAction\tAction\nLaunchApp\t226\tINSTALLDIR\twscript.exe "[INSTALLDIR]launcher.vbs"\t\n' \
    > "$STAGE/CustomAction.idt"
(cd "$STAGE" && "$MSIBUILD" "$OUT" -i CustomAction.idt)
rm -rf "$STAGE"
echo
echo "✅ MSI generado: $OUT"
