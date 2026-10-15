variable "region" {
  description = "Región del bucket y de la función. CloudFront es global."
  type        = string
  default     = "us-east-1"
}

variable "perfil" {
  description = "Perfil de la AWS CLI. Con null se usan las credenciales del entorno."
  type        = string
  default     = null
}

variable "nombre" {
  description = "Prefijo de los recursos."
  type        = string
  default     = "agrocebada"
}

variable "carpeta_sitio" {
  description = "Carpeta con el sitio ya construido; cada archivo se sube tal cual al bucket."
  type        = string
  default     = "../web/dist"
}

variable "paquete_api" {
  description = "ZIP de la función, generado con `uv run python api/empaquetar.py`."
  type        = string
  default     = "../api/dist/agrocebada_api.zip"
}

variable "memoria_api" {
  description = "Memoria de la función en MB; también define su CPU."
  type        = number
  default     = 1024
}

variable "dominio" {
  description = "Subdominio propio para el sitio (p. ej. agrocebada.foor.dev). Con null se usa solo el dominio de CloudFront."
  type        = string
  default     = null
}
