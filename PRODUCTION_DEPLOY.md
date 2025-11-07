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
CSRF_TRUSTED_ORIGINS=https://backavanza.onrender.com,https://front-avanza.vercel.app
```

**⚠️ IMPORTANTE para CORS:**
- En Render, agrega exactamente: `CORS_ALLOWED_ORIGINS=https://front-avanza.vercel.app`
- NO incluyas espacios ni comillas
- Usa la URL exacta de tu frontend en Vercel

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
# 1. Verificar configuración CORS y debug
curl https://backavanza.onrender.com/api/debug-frontend/

# 2. Test de preflight CORS (OPTIONS)
curl -X OPTIONS https://backavanza.onrender.com/api/token/ \
  -H "Origin: https://front-avanza.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" -v

# 3. Test de autenticación
curl -X POST https://backavanza.onrender.com/api/token/ \
  -H "Content-Type: application/json" \
  -H "Origin: https://front-avanza.vercel.app" \
  -d '{"username":"tu_usuario","password":"tu_password"}' -v

# 4. Test dashboard (con token)
curl https://backavanza.onrender.com/api/dashboard/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Origin: https://front-avanza.vercel.app" -v
```

### ⚠️ DIAGNÓSTICO DE ERRORES CORS:

**Error**: `No 'Access-Control-Allow-Origin' header`
**Solución**: 
1. Verificar que `CORS_ALLOWED_ORIGINS` esté configurado en Environment de Render
2. Usar la URL exacta del frontend (https://front-avanza.vercel.app)
3. Verificar que `corsheaders` esté antes de `CommonMiddleware` en MIDDLEWARE

## 📝 VARIABLES DE ENTORNO COMPLETAS:

Ver archivo `.env.example` para la lista completa y documentada.