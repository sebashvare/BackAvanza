# Guía de Integración Frontend - Sistema de Imágenes Protegidas

## Resumen
Este documento explica cómo integrar correctamente el sistema de imágenes protegidas desde el frontend (Svelte) con el backend Django.

## Problema Actual
Las imágenes de los clientes contienen información sensible y deben estar protegidas. Solo usuarios autenticados pueden acceder a ellas.

## Arquitectura
1. **URLs Públicas**: Para usuarios no autenticados (URLs directas de Cloudinary)
2. **URLs Protegidas**: Para usuarios autenticados (a través del proxy seguro)

## Implementación Frontend

### 1. Verificar Autenticación
```javascript
// Verificar si el usuario está autenticado
const isAuthenticated = !!localStorage.getItem('access_token');
```

### 2. Componente SecureImage Mejorado
```javascript
// SecureImage.svelte
<script>
  import { onMount } from 'svelte';
  
  export let src = '';
  export let alt = '';
  export let className = '';
  
  let imageSrc = '';
  let loading = true;
  let error = false;
  
  onMount(async () => {
    try {
      const token = localStorage.getItem('access_token');
      
      if (!token) {
        // Si no hay token, usar la URL pública directa
        imageSrc = src;
        loading = false;
        return;
      }
      
      // Verificar si la URL es del proxy seguro
      if (src.includes('/api/secure-media/')) {
        // Es una URL protegida, necesita autenticación
        const response = await fetch(src, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (response.ok) {
          const blob = await response.blob();
          imageSrc = URL.createObjectURL(blob);
        } else {
          error = true;
        }
      } else {
        // Es una URL pública directa
        imageSrc = src;
      }
    } catch (err) {
      console.error('Error cargando imagen:', err);
      error = true;
    } finally {
      loading = false;
    }
  });
</script>

{#if loading}
  <div class="loading">Cargando...</div>
{:else if error}
  <div class="error">Error cargando imagen</div>
{:else}
  <img {src}={imageSrc} {alt} class={className} />
{/if}
```

### 3. Testear Autenticación
Antes de intentar cargar imágenes protegidas, verificar que la autenticación funciona:

```javascript
// Función para testear autenticación
async function testAuth() {
  const token = localStorage.getItem('access_token');
  
  if (!token) {
    console.log('No hay token disponible');
    return false;
  }
  
  try {
    const response = await fetch('/api/test-auth/', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    if (response.ok) {
      const data = await response.json();
      console.log('Autenticación exitosa:', data);
      return true;
    } else {
      console.log('Token inválido o expirado');
      return false;
    }
  } catch (error) {
    console.error('Error verificando autenticación:', error);
    return false;
  }
}
```

## Endpoints Backend

### 1. Test de Autenticación
- **URL**: `GET /api/test-auth/`
- **Headers**: `Authorization: Bearer <token>`
- **Respuesta**: Información del usuario autenticado

### 2. Proxy de Imágenes Seguras
- **URL**: `GET /api/secure-media/<path>`
- **Headers**: `Authorization: Bearer <token>`
- **Respuesta**: Imagen binaria con headers de seguridad

## Flujo de Trabajo

1. **Usuario se autentica** → Obtiene token JWT
2. **Frontend solicita lista de clientes** → API retorna URLs protegidas si está autenticado
3. **Frontend carga imágenes** → Usa el componente SecureImage con token JWT
4. **Backend valida token** → Sirve imagen desde Cloudinary si es válido

## Debugging

### Logs del Backend
El proxy incluye logs detallados:
```
🔑 [PROXY] Iniciando proxy para: media/clientes/2025/10/07/DOCUMENTO.jpeg
🔓 [PROXY] Path decodificado: media/clientes/2025/10/07/DOCUMENTO.jpeg
✅ [PROXY] Usuario autenticado: admin
🔗 [PROXY] URL de Cloudinary: https://res.cloudinary.com/...
✅ [PROXY] Imagen encontrada, sirviendo archivo
```

### Verificaciones Frontend
1. Verificar que el token existe en localStorage
2. Verificar que el header Authorization se envía correctamente
3. Verificar que la URL del proxy es correcta

## Casos de Error Comunes

### Error 401 - No Autorizado
- **Causa**: Token faltante, inválido o expirado
- **Solución**: Verificar token y renovar si es necesario

### Error 404 - Archivo No Encontrado
- **Causa**: Path incorrecto o archivo no existe en Cloudinary
- **Solución**: Verificar que el path preserva la extensión del archivo

### Error 500 - Error Interno
- **Causa**: Problemas de conectividad con Cloudinary
- **Solución**: Verificar configuración de Cloudinary

## Mejores Prácticas

1. **Siempre verificar autenticación** antes de intentar cargar imágenes protegidas
2. **Implementar fallbacks** a URLs públicas cuando la autenticación falla
3. **Cachear tokens** y renovarlos automáticamente
4. **Manejar errores** gracefully con mensajes informativos
5. **Usar loading states** para mejor UX

## Consideraciones de Seguridad

- Las URLs protegidas requieren autenticación válida
- Los tokens JWT deben renovarse periódicamente
- Las imágenes servidas incluyen headers de seguridad adicionales
- El acceso a las imágenes queda registrado en los logs del servidor