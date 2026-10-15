# Función que reentrena E_JK y estima las 59 parcelas (código en api/).
# Su URL usa autenticación AWS_IAM: solo CloudFront, firmando con OAC, puede invocarla.

data "aws_iam_policy_document" "confianza_lambda" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "api" {
  name               = "${var.nombre}-api"
  assume_role_policy = data.aws_iam_policy_document.confianza_lambda.json
}

resource "aws_iam_role_policy_attachment" "api_registros" {
  role       = aws_iam_role.api.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${var.nombre}-api"
  retention_in_days = 14
}

# El ZIP (~24 MB) es demasiado grande para enviarlo dentro de CreateFunction
# ("bufio.Scanner: token too long"), así que pasa por un bucket privado aparte
# (el del sitio no sirve: CloudFront lo publicaría).
resource "aws_s3_bucket" "paquete_api" {
  bucket        = "${var.nombre}-paquete-${data.aws_caller_identity.actual.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "paquete_api" {
  bucket                  = aws_s3_bucket.paquete_api.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "paquete_api" {
  bucket      = aws_s3_bucket.paquete_api.id
  key         = "agrocebada_api.zip"
  source      = var.paquete_api
  source_hash = filemd5(var.paquete_api)

  depends_on = [aws_s3_bucket_public_access_block.paquete_api]
}

resource "aws_lambda_function" "api" {
  function_name    = "${var.nombre}-api"
  description      = "Reentrena E_JK con las 138 parcelas conocidas y estima las 59 (Reto AgroCebada 2026)"
  role             = aws_iam_role.api.arn
  runtime          = "python3.13"
  architectures    = ["arm64"]
  handler          = "agrocebada_api.handler.handler"
  s3_bucket        = aws_s3_object.paquete_api.bucket
  s3_key           = aws_s3_object.paquete_api.key
  source_code_hash = filebase64sha256(var.paquete_api)
  memory_size      = var.memoria_api
  timeout          = 30

  depends_on = [aws_iam_role_policy_attachment.api_registros, aws_cloudwatch_log_group.api]
}

resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "AWS_IAM"
}

# CloudFront necesita los dos permisos para invocar una URL de función con OAC.
resource "aws_lambda_permission" "cloudfront_url" {
  statement_id           = "CloudFrontInvokeFunctionUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.api.function_name
  principal              = "cloudfront.amazonaws.com"
  source_arn             = aws_cloudfront_distribution.sitio.arn
  function_url_auth_type = "AWS_IAM"
}

resource "aws_lambda_permission" "cloudfront_invocar" {
  statement_id  = "CloudFrontInvokeFunction"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "cloudfront.amazonaws.com"
  source_arn    = aws_cloudfront_distribution.sitio.arn
}
