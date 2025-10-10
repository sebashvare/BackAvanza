# 📦 Configuración de Cloudinary para Almacenamiento de Media

Este proyecto usa **Cloudinary** para almacenar archivos media (imágenes de clientes) en producción y **almacenamiento local** en desarrollo.

## 🎯 ¿Por qué Cloudinary?

- **Render tiene sistema de archivos efímero**: Los archivos se pierden al redesplegar
- **Plan gratuito generoso**: 25 GB de almacenamiento + 25 GB de ancho de banda/mes
- **CDN global**: Entrega rápida de imágenes en todo el mundo
- **Optimización automática**: Compresión y transformación de imágenes

## 🔧 Configuración en Desarrollo (Localhost)

En tu archivo `.env` local:

```properties
USE_CLOUDINARY=false
```

**NO necesitas configurar credenciales de Cloudinary** en desarrollo. Los archivos se guardarán en la carpeta `media/` local.

## 🚀 Configuración en Producción (Render)

### Paso 1: Crear cuenta en Cloudinary

1. Ir a: https://cloudinary.com/users/register/free
2. Registrarse (plan gratuito)
3. Confirmar email

### Paso 2: Obtener credenciales

1. Ir al Dashboard: https://cloudinary.com/console
2. Copiar las credenciales:
   ```
   Cloud name: dxxxxxxxxxxxx
   API Key: 123456789012345
   API Secret: abcdefghijklmnopqrstuvwxyz
   ```

### Paso 3: Configurar variables de entorno en Render

1. Ir al dashboard de tu servicio en Render
2. Settings → Environment
3. Agregar las siguientes variables:

```bash
USE_CLOUDINARY=true
CLOUDINARY_CLOUD_NAME=tu_cloud_name_aqui
CLOUDINARY_API_KEY=tu_api_key_aqui
CLOUDINARY_API_SECRET=tu_api_secret_aqui
```

4. Guardar cambios
5. Render redesplegar automáticamente

### Paso 4: Verificar configuración

Después del deploy, revisa los logs de Render. Deberías ver:

```
✅ [PRODUCCIÓN] Configurando Cloudinary para archivos media
   Cloud Name: tu_cloud_name
```

## 📊 Comportamiento según entorno

| Aspecto | Desarrollo (Localhost) | Producción (Render) |
|---------|------------------------|---------------------|
| **Variable USE_CLOUDINARY** | `false` | `true` |
| **Almacenamiento** | Local (`media/`) | Cloudinary |
| **Persistencia** | ✅ Sí | ✅ Sí |
| **Velocidad** | ⚡ Instantánea | 🌐 CDN global |
| **Costo cuota Cloudinary** | 🆓 No consume | ✅ Consume |
| **URL de archivos** | `http://localhost:8000/media/...` | `https://res.cloudinary.com/...` |

## 🧪 Probar la configuración

### En Localhost:

```bash
python manage.py shell
```

```python
from django.core.files.storage import default_storage
print(default_storage.__class__.__name__)
# Debería mostrar: FileSystemStorage
```

### En Render (después del deploy):

1. Subir una imagen desde el frontend
2. Verificar que se guardó en Cloudinary:
   - Ir a: https://cloudinary.com/console/media_library
   - Buscar la imagen en la carpeta `media/`

## 🔄 Migrar archivos existentes a Cloudinary (Opcional)

Si ya tienes archivos en producción que se perdieron:

1. Descargar los archivos desde tu carpeta local `media/`
2. Subir manualmente a Cloudinary:
   - Ir a: https://cloudinary.com/console/media_library
   - Upload → Upload files
   - Mantener la misma estructura de carpetas

## ⚠️ Notas importantes

1. **No versionar credenciales**: Nunca subas el archivo `.env` con credenciales reales a GitHub
2. **Plan gratuito**: 25GB almacenamiento + 25GB ancho de banda/mes (más que suficiente para empezar)
3. **URLs de imágenes**: Cambiarán de local a Cloudinary, pero el frontend las maneja automáticamente
4. **Backup**: Cloudinary mantiene los archivos permanentemente (no se pierden)

## 🆘 Troubleshooting

### Error: "No module named 'cloudinary'"
```bash
pip install django-cloudinary-storage cloudinary
```

### Error: "CLOUDINARY_CLOUD_NAME not configured"
- Verificar que las variables de entorno estén configuradas en Render
- Verificar que `USE_CLOUDINARY=true` en producción

### Las imágenes no se ven en producción
1. Verificar en Cloudinary que los archivos se subieron
2. Revisar los logs de Render para errores
3. Verificar que las URLs en la BD apunten a Cloudinary

### ¿Cómo volver a almacenamiento local?
En Render, cambiar:
```bash
USE_CLOUDINARY=false
```
**⚠️ Advertencia**: Perderás los archivos al redesplegar

## 📚 Recursos adicionales

- Documentación oficial: https://cloudinary.com/documentation
- Dashboard: https://cloudinary.com/console
- Media Library: https://cloudinary.com/console/media_library
- Soporte: https://support.cloudinary.com/

## 💰 Monitorear uso

- Dashboard → Usage: https://cloudinary.com/console/usage
- Alertas automáticas cuando te acerques al límite gratuito
- Upgrade disponible si necesitas más espacio
