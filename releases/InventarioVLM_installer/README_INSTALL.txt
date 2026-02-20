InventarioVLM - Paquete de instalación

Contenido de esta carpeta:
- InventarioVLM.exe       -> ejecutable principal (GUI)
- inventariovlm.db        -> base de datos SQLite usada por la app
- icons/                  -> iconos usados por la app/shortcuts
- install.ps1             -> script PowerShell para instalar (copia archivos y crea accesos directos)
- uninstall.ps1           -> script PowerShell para desinstalar
- InventarioVLM_installer.iss -> script para Inno Setup (opcional)

Instrucciones rápidas (PowerShell, ejecutar como Administrador):
1) Copiar esta carpeta al equipo objetivo (o transferir el ZIP y extraer).
2) Abrir PowerShell como Administrador y navegar a esta carpeta.
3) Ejecutar:
   .\install.ps1
   (o ejecutar: powershell -ExecutionPolicy Bypass -File .\install.ps1)

El instalador copia todos los archivos al directorio por defecto "C:\\Program Files\\InventarioVLM" y crea accesos directos en el Escritorio y en el Menú Inicio.

Notas:
- Si prefiere un instalador .exe nativo, use Inno Setup con el archivo `InventarioVLM_installer.iss` que se incluye (requiere Inno Setup instalado).
- Asegúrese de que `InventarioVLM.exe` y `inventariovlm.db` estén presentes en esta carpeta antes de ejecutar `install.ps1`.
- Si la aplicación no encuentra las tablas, asegúrese de que `inventariovlm.db` contenga las tablas esperadas. Puede abrir la DB con DB Browser for SQLite para verificar.

Soporte:
Si desea que yo genere el instalador .exe usando Inno Setup en esta máquina, indique si Inno Setup está disponible o si desea que genere un paquete ZIP listo para desplegar.