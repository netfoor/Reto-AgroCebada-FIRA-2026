# 07 Plataforma en la nube

*Prompts de Fortino Romero Mantilla · IA usada: Claude (Anthropic)*

## Un primer prototipo de la interfaz
**Lo que pedimos:** "Tengo claro qué debe poder hacer la plataforma: consultar, ejecutar, explicar, mostrar la parte de inclusión financiera y responder las preguntas guía. Con el código y el contexto que llevamos en el repositorio, arma un primer prototipo con una sección para cada una. Andrea y Jared hicieron sus propias propuestas; úsalas solo como referencia de ideas, sin copiar su texto ni su código."

**Qué salió:** un prototipo donde cada sección responde a una de esas funciones. Lo revisamos y pedimos cambios de diseño.

## Primero el back, luego el front
**Lo que pedimos:** "Yo prefiero tener el modelo y los datos en la nube antes de pulir la página, en el mismo repositorio que el modelo, con Terraform y AWS. Dime qué riesgos le ves a ese orden antes de empezar."

**Qué salió:** una función en la nube que reentrena el modelo con las 138 parcelas y produce un CSV idéntico al de la entrega, y la infraestructura escrita como código. La desplegamos y probamos nosotros.

## Correcciones de diseño
**Lo que pedimos:** "El contenido está bien, pero la tipografía no me convence. Quiero acercarla al estilo del sitio de AWS UG Puebla, con un poco más de espacio y negritas, sin exagerar. Reordena la portada con los logos como en mi boceto, quita la barra de pestañas y el marco negro del indicador de etapa, haz más lenta la unión de capas y que se deshaga al regresar, y evita los recuadros redondeados que se ven genéricos."

**Qué salió:** el sitio definitivo con un indicador de sección minimalista, la animación ligada al scroll y una versión propia para teléfono. Revisamos cada versión en el celular y pedimos ajustes puntuales (el círculo del minimapa, la gráfica cortada).

## Dominio propio y documentación del diseño
**Lo que pedimos:** "Quiero publicar el sitio en agrocebada.foor.dev. Explícame los pasos del certificado y de los registros DNS para que yo los cree. Después, con base en el sitio como quedó, ayúdame a redactar una guía corta con las decisiones de diseño para que el equipo siga el mismo estilo."

**Qué salió:** el certificado y el subdominio configurados (los registros DNS los creamos nosotros) y una guía de diseño para el equipo.
