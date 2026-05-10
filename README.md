# Abastecimiento Total — API

Backend en FastAPI + MongoDB para el sistema de cotizaciones.

## Estructura del proyecto

```
abastecimiento-api/
├── app/
│   ├── core/
│   │   ├── config.py        # Settings desde .env
│   │   ├── database.py      # Conexión Motor + índices
│   │   └── security.py      # JWT + bcrypt
│   ├── routers/
│   │   ├── auth.py          # POST /api/auth/login, /register, /me
│   │   ├── cotizaciones.py  # CRUD + cambio de estado
│   │   ├── compras.py       # Compra + items + parciales
│   │   ├── documentos.py    # Upload/download archivos
│   │   └── costos_fijos.py  # Config global
│   ├── schemas/
│   │   ├── base.py          # PyObjectId + MongoBaseModel
│   │   ├── cotizacion.py    # Todos los modelos de cotización
│   │   ├── compra.py        # Compra + items + parciales
│   │   ├── documento.py     # Tipos de documento
│   │   └── user.py          # User + auth
│   ├── services/
│   │   ├── cotizacion_service.py  # Lógica de negocio + cálculos
│   │   ├── compra_service.py      # Lógica de compras parciales
│   │   └── storage_service.py     # Archivos (local / S3)
│   └── main.py              # App FastAPI + middlewares
├── seed.py                  # Datos iniciales
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Instalación local

```bash
# 1. Clonar y entrar al directorio
cd abastecimiento-api

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus valores

# 5. Levantar MongoDB (necesitas tenerlo instalado o usar Docker)
docker run -d -p 27017:27017 --name mongo mongo:7

# 6. Cargar datos iniciales
python seed.py

# 7. Levantar el servidor
uvicorn app.main:app --reload
```

## Con Docker Compose (recomendado)

```bash
cp .env.example .env
docker-compose up -d
python seed.py   # Solo la primera vez
```

API disponible en: http://localhost:8000
Documentación Swagger: http://localhost:8000/docs

## Endpoints principales

### Auth
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | /api/auth/login | Login, retorna JWT |
| GET | /api/auth/me | Usuario actual |
| POST | /api/auth/register | Crear usuario |

### Cotizaciones
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /api/cotizaciones | Listar (filtros: estado, ejecutivo_id) |
| POST | /api/cotizaciones | Crear nueva |
| GET | /api/cotizaciones/{id} | Obtener una |
| PATCH | /api/cotizaciones/{id} | Editar |
| PATCH | /api/cotizaciones/{id}/estado | Cambiar estado |
| DELETE | /api/cotizaciones/{id} | Eliminar borrador |

### Compras
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /api/compras/cotizacion/{id} | Compra + items de una cotización |
| GET | /api/compras/items/{item_id} | Un item específico |
| POST | /api/compras/items/{item_id}/parciales | Registrar compra parcial |

### Documentos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /api/documentos/cotizacion/{id} | Listar docs de una cotización |
| POST | /api/documentos/cotizacion/{id} | Subir documento (multipart) |
| DELETE | /api/documentos/{doc_id} | Eliminar documento |

### Costos Fijos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /api/costos-fijos | Listar todos |
| POST | /api/costos-fijos | Crear |
| PATCH | /api/costos-fijos/{id} | Actualizar |
| DELETE | /api/costos-fijos/{id} | Eliminar |

## Flujo de estados de una cotización

```
borrador → enviada → aprobada → en_compra → comprada
                  ↘ rechazada
                  ↘ expirada
```

Al pasar a **aprobada**, el sistema automáticamente:
1. Crea un documento `compra` asociado
2. Crea un `compra_item` por cada producto de la cotización

Al agregar parciales hasta completar todos los items, el sistema automáticamente:
1. Marca la compra como `completada`
2. Actualiza la cotización a estado `comprada`

## Subir un documento (ejemplo con curl)

```bash
curl -X POST "http://localhost:8000/api/documentos/cotizacion/COT_ID" \
  -H "Authorization: Bearer TU_TOKEN" \
  -F "tipo=factura_compra" \
  -F "monto=450000" \
  -F "numero_doc=FAC-001" \
  -F "file=@factura.pdf"
```

## Credenciales iniciales (seed)

| Nombre | Email | Contraseña |
|--------|-------|------------|
| Gonzalo Galvez | ggalvezb@abastecimientototal.cl | at2025 |
| Joel Caceres | jcaceresf@abastecimientototal.cl | at2025 |
| Gabriela Soto | gsotov@abastecimientototal.cl | at2025 |
| Felipe Valdenegro | fvaldenegro@abastecimientototal.cl | at2025 |

> ⚠️ Cambiar contraseñas en producción.
