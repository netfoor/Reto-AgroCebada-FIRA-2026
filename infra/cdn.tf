# Una sola distribución: el sitio desde S3 y la API desde la URL de la función, en el mismo dominio.

data "aws_cloudfront_cache_policy" "optimizada" {
  name = "Managed-CachingOptimized"
}

data "aws_cloudfront_cache_policy" "sin_cache" {
  name = "Managed-CachingDisabled"
}

# Reenvía la consulta (?formato=csv) pero no el Host: la URL de la función exige su propio dominio.
data "aws_cloudfront_origin_request_policy" "todo_menos_host" {
  name = "Managed-AllViewerExceptHostHeader"
}

data "aws_cloudfront_response_headers_policy" "seguridad" {
  name = "Managed-SecurityHeadersPolicy"
}

resource "aws_cloudfront_origin_access_control" "s3" {
  name                              = "${var.nombre}-s3"
  description                       = "Lectura del bucket del sitio"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_origin_access_control" "lambda" {
  name                              = "${var.nombre}-lambda"
  description                       = "Invocación firmada de la URL de la función"
  origin_access_control_origin_type = "lambda"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

locals {
  # https://xxxx.lambda-url.<region>.on.aws/  →  xxxx.lambda-url.<region>.on.aws
  dominio_api = split("/", aws_lambda_function_url.api.function_url)[2]
}

resource "aws_cloudfront_distribution" "sitio" {
  enabled             = true
  comment             = "Reto AgroCebada 2026: sitio y API"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"
  http_version        = "http2and3"
  is_ipv6_enabled     = true
  aliases             = var.dominio == null ? [] : [var.dominio]

  origin {
    origin_id                = "sitio"
    domain_name              = aws_s3_bucket.sitio.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.s3.id
  }

  origin {
    origin_id                = "api"
    domain_name              = local.dominio_api
    origin_access_control_id = aws_cloudfront_origin_access_control.lambda.id

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id           = "sitio"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.optimizada.id
    response_headers_policy_id = data.aws_cloudfront_response_headers_policy.seguridad.id
  }

  ordered_cache_behavior {
    path_pattern               = "/api/*"
    target_origin_id           = "api"
    viewer_protocol_policy     = "https-only"
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.sin_cache.id
    origin_request_policy_id   = data.aws_cloudfront_origin_request_policy.todo_menos_host.id
    response_headers_policy_id = data.aws_cloudfront_response_headers_policy.seguridad.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = var.dominio == null
    acm_certificate_arn            = var.dominio == null ? null : aws_acm_certificate_validation.dominio[0].certificate_arn
    ssl_support_method             = var.dominio == null ? null : "sni-only"
    minimum_protocol_version       = var.dominio == null ? "TLSv1" : "TLSv1.2_2021"
  }
}
