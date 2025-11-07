# 🚀 GUÍA DE DEPLOY A PRODUCCIÓN

## ✅ CHECKLIST PREVIA AL DEPLOY

### 1. Variables de Entorno OBLIGATORIAS en Render:

```env
SECRET_KEY=una-clave-super-secreta-de-minimo-50-caracteres
DEBUG=False
DATABASE_URL=postgresql://... (usar Internal Database URL)
USE_CLOUDINARY=True
CLOUDINARY_CLOUD_NAME=tu_cloud_name
CLOUDINARY_API_KEY=123456789012345  
CLOUDINARY_API_SECRET=tu_api_secret
CORS_ALLOWED_ORIGINS=https://front-avanza.vercel.app
```

### 2. Configuración de Render:

**Build Command:**
```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
```

**Start Command:**
```bash
gunicorn backend.wsgi:application
```

### 3. Configuración de Base de Datos:

- ✅ PostgreSQL configurado en Render
- ✅ Migraciones automáticas en build
- ✅ Django ORM compatible PostgreSQL/SQLite

### 4. Configuración de Archivos Media:

- ✅ Cloudinary configurado para producción
- ✅ Sistema local para desarrollo
- ✅ Variables de entorno para alternar

### 5. Seguridad:

- ✅ DEBUG=False por defecto
- ✅ SECRET_KEY obligatoria en producción  
- ✅ CORS restrictivo a dominios específicos
- ✅ HTTPS enforced con HSTS
- ✅ Configuración segura de cookies

### 6. Autenticación:

- ✅ JWT por defecto con IsAuthenticated
- ✅ TokenRefreshView configurado correctamente
- ✅ Endpoints protegidos

## ⚠️ POSIBLES PROBLEMAS Y SOLUCIONES:

### Error: "SECRET_KEY no está definida"
**Solución:** Agrega SECRET_KEY en Environment de Render

### Error: "Variables de entorno faltantes"  
**Solución:** Revisa que todas las variables estén en Environment de Render

### Error: "CORS blocked"
**Solución:** Verifica CORS_ALLOWED_ORIGINS incluye tu dominio exacto de Vercel

### Error: Base de datos
**Solución:** Usa "Internal Database URL" completa de PostgreSQL de Render

### Error: Archivos media no se ven
**Solución:** Verifica configuración completa de Cloudinary

## 🔧 COMANDOS DE VERIFICACIÓN POST-DEPLOY:

```bash
# Verificar configuración
curl https://tu-backend.onrender.com/api/debug-frontend/

# Test de autenticación  
curl -X POST https://tu-backend.onrender.com/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"tu_usuario","password":"tu_password"}'

# Test dashboard (con token)
curl https://tu-backend.onrender.com/api/dashboard/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 📝 VARIABLES DE ENTORNO COMPLETAS:

Ver archivo `.env.example` para la lista completa y documentada.