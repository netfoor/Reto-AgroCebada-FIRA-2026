output "url_sitio" {
  description = "Dirección pública del sitio (para el jurado)."
  value       = "https://${var.dominio == null ? aws_cloudfront_distribution.sitio.domain_name : var.dominio}"
}

output "url_cloudfront" {
  description = "Dominio de la distribución; el CNAME del subdominio apunta aquí."
  value       = aws_cloudfront_distribution.sitio.domain_name
}

output "dns_validacion" {
  description = "CNAME que ACM pide para validar el certificado (crearlo en Cloudflare, sin proxy)."
  value = var.dominio == null ? [] : [for o in aws_acm_certificate.dominio[0].domain_validation_options : {
    nombre = o.resource_record_name
    tipo   = o.resource_record_type
    valor  = o.resource_record_value
  }]
}

output "url_api" {
  description = "Reentrenamiento en la nube."
  value       = "https://${var.dominio == null ? aws_cloudfront_distribution.sitio.domain_name : var.dominio}/api/reentrenar"
}

output "bucket_sitio" {
  value = aws_s3_bucket.sitio.id
}

output "distribucion" {
  value = aws_cloudfront_distribution.sitio.id
}

output "funcion_api" {
  value = aws_lambda_function.api.function_name
}

output "archivos_publicados" {
  value = length(aws_s3_object.sitio)
}
