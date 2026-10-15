# Despliegue en AWS

El sitio y la API quedan en un solo dominio de CloudFront. El jurado abre una dirección y no descarga nada.

```
Navegador ──► CloudFront ──┬── /*      ──► S3 privado (sitio y datos)
                           └── /api/*  ──► Lambda (URL de función con IAM)
```

| Pieza | Qué hace |
|---|---|
| S3 | Guarda el sitio construido (`web/dist`). Es privado: solo CloudFront lo lee, con control de acceso de origen (OAC). |
| Lambda `agrocebada-api` | Python 3.13 en arm64. `GET /api/reentrenar` ajusta E_JK con las 138 parcelas y estima las 59; el CSV que produce debe tener la misma SHA-256 que `resultados/04_seleccion_modelo_final/predicciones_59.csv`. `?formato=csv` devuelve ese archivo y `GET /api/salud` muestra versiones e insumos verificados. |
| CloudFront | HTTPS, compresión y encabezados de seguridad. Firma las llamadas a la función, así que su URL directa no responde a nadie más. |

Todo se crea con Terraform; no hay pasos manuales en la consola.

## Requisitos

- [uv](https://docs.astral.sh/uv/) y Terraform 1.6 o posterior.
- Credenciales de AWS: un perfil de la AWS CLI (`aws configure` o `aws sso login`) o variables de entorno.

## Primer despliegue

Desde la raíz del repositorio:

```bash
# 1. Comprobar sin AWS que la API reproduce la entrega
uv run python api/verificar.py

# 2. Empaquetar la función (api/dist/agrocebada_api.zip, ~23 MB)
uv run python api/empaquetar.py

# 3. Construir el sitio en web/dist
uv run --group geo python scripts/exportar_web.py
(cd web && npm ci && npm run build)

# 4. Crear la infraestructura y publicar
cd infra
terraform init
terraform apply                    # con perfil o región propios: -var perfil=mi-perfil -var region=us-east-1

# 5. Probar
curl -s "$(terraform output -raw url_sitio)/api/salud"
```

`terraform apply` muestra el plan y pide confirmación. La primera vez CloudFront tarda unos minutos en propagarse; mientras tanto la URL puede responder con error.

Después del primer `terraform init`, versiona `infra/.terraform.lock.hcl`: fija la versión exacta del proveedor de AWS para todo el equipo.

## Subdominio propio (agrocebada.foor.dev)

`terraform.tfvars` fija `dominio = "agrocebada.foor.dev"`. El DNS de foor.dev está en Cloudflare, así que dos registros se crean a mano, ambos **sin proxy** (nube gris, «DNS only»):

```bash
cd infra
# 1. Pedir el certificado (us-east-1) y ver el CNAME que lo valida
terraform apply -target=aws_acm_certificate.dominio
terraform output dns_validacion
```

2. En Cloudflare, crea ese CNAME (nombre y valor tal cual, sin proxy).
3. `terraform apply`: espera a que ACM emita el certificado (unos minutos) y agrega el subdominio a CloudFront.
4. En Cloudflare, crea `agrocebada` → CNAME → el valor de `terraform output url_cloudfront`, sin proxy.

El dominio de CloudFront (`url_cloudfront`) sigue funcionando. El CNAME de validación debe quedarse: ACM lo usa para renovar el certificado.

## Publicar cambios

- **Sitio:** construye `web/dist` y vuelve a correr `terraform apply`. Solo se suben los archivos que cambiaron. Los archivos de `_astro/` llevan huella en el nombre y se guardan un año; el resto se revalida en cada visita, así que no hace falta invalidar la caché.
- **API:** `uv run python api/empaquetar.py` y `terraform apply`. El ZIP es determinista: si nada cambió, la función no se vuelve a desplegar.

## El sitio

`web/dist` es el sitio construido con Astro ([`web/`](../web/README.md)): `uv run --group geo python scripts/exportar_web.py` actualiza sus datos y `npm ci && npm run build`, dentro de `web/`, arma la carpeta. Terraform sube cada archivo con su tipo de contenido y borra del bucket lo que ya no está en `web/dist`.

## Variables

| Variable | Por defecto | Uso |
|---|---|---|
| `region` | `us-east-1` | Región del bucket y la función. Otra región sirve si ofrece Lambda con Python 3.13 en arm64. |
| `perfil` | `null` | Perfil de la AWS CLI; `null` usa las credenciales del entorno. |
| `nombre` | `agrocebada` | Prefijo de los recursos. El bucket se llama `agrocebada-sitio-<cuenta>`. |
| `carpeta_sitio` | `../web/dist` | Sitio ya construido. |
| `paquete_api` | `../api/dist/agrocebada_api.zip` | ZIP de la función. |
| `memoria_api` | `1024` | Memoria de la función en MB. |
| `dominio` | `null` (en `terraform.tfvars`: `agrocebada.foor.dev`) | Subdominio propio; con `null` solo queda el dominio de CloudFront. |

## Costo y retiro

Con el tráfico de una evaluación (decenas o cientos de visitas), S3, CloudFront y Lambda quedan dentro de la capa gratuita o en centavos de dólar. Para retirar todo:

```bash
cd infra && terraform destroy
```

El bucket se borra junto con sus archivos (`force_destroy`).

## Seguridad

- El bucket bloquea todo acceso público; su política solo permite `s3:GetObject` a esta distribución.
- La URL de la función usa `AWS_IAM`. Solo esta distribución tiene permiso de invocarla.
- La función solo acepta `GET` y `HEAD`, no guarda nada y verifica la SHA-256 de cada insumo antes de usarlo.
- El estado de Terraform (`terraform.tfstate`) queda en tu equipo y no se versiona.
