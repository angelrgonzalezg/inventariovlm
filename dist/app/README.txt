Inventariovlm - Portable

Contenido:
- app.exe             -> Ejecutable principal
- inventariovlm.db    -> Base de datos (editable)
- pdf\               -> PDFs usados por la app (inventory_<name>.pdf)
- start.bat           -> Script para iniciar la app (doble clic)

Instrucciones de uso:
1. Copia la carpeta completa `app` (o el ZIP `Inventariovlm_portable.zip`) al pendrive.
2. En el pendrive, abre la carpeta `app` y ejecuta `start.bat` (doble clic). También puedes ejecutar `app.exe` directamente.
3. La base de datos `inventariovlm.db` está al lado del ejecutable: cualquier cambio se guarda ahí.
4. Para exportar datos a Excel, la app usa `openpyxl` si está disponible; en caso contrario genera un CSV y lo abre con la aplicación por defecto (Excel en Windows).

Notas:
- Esta distribución fue construida con PyInstaller en modo "onedir" para permitir mantener la base de datos editable.
- Si encuentras problemas al ejecutar en otra máquina, asegúrate de que sea Windows x64 compatible.
- Tamaño: la carpeta contiene dependencias como pandas/numpy y puede ser grande.

Contacto:
- Si quieres que adapte el paquete (acceso directo, icono, instalador), dime qué prefieres.
