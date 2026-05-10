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

