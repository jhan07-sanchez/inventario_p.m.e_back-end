# Backend ERP P.M.E. — Sistema SaaS Multi-Tenant

## Variables de Entorno de Soporte y Suscripciones

Para configurar los canales de atención y renovación en las respuestas del API para empresas en modo lectura o sin suscripción activa (`SUBSCRIPTION_EXPIRED` y `SUBSCRIPTION_REQUIRED`):

| Variable | Tipo | Descripción | Ejemplo |
| :--- | :--- | :--- | :--- |
| `SUPPORT_WHATSAPP` | `string` | Número de WhatsApp para soporte/ventas (código de país sin signos ni espacios). Si está configurado, el backend genera enlaces prellenados `https://wa.me/{numero}?text=...`. Si está vacío, retorna `null`. | `573001234567` |
| `SUPPORT_EMAIL` | `string` | Correo electrónico de ventas/soporte para solicitudes de renovación. Si está configurado, el backend genera enlaces `mailto:{email}?subject=...`. Si está vacío, retorna `null`. | `ventas@inventariopme.com` |

Si ambas variables se encuentran vacías o no configuradas, el backend entrega `null` en ambos campos y el frontend muestra el mensaje estático *"Contacta a tu administrador para renovar."* sin botones externos.
